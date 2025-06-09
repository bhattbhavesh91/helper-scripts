import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup
from peft import LoraConfig, get_peft_model, TaskType
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from tqdm import tqdm
import logging
import wandb
from typing import Dict, List, Tuple, Optional
import os
from dataclasses import dataclass
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuration class for training parameters"""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    max_length: int = 512
    batch_size: int = 16
    learning_rate: float = 2e-4
    num_epochs: int = 3
    warmup_steps: int = 100
    weight_decay: float = 0.01
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0
    save_steps: int = 500
    eval_steps: int = 250
    output_dir: str = "./lora_embedding_model"
    use_wandb: bool = False
    wandb_project: str = "embedding-lora-finetuning"

class AddressSimilarityDataset(Dataset):
    """
    Dataset class for address similarity training data
    
    Expected CSV format:
    - address_1: First address string
    - address_2: Second address string  
    - similarity_score: Float between 0-1 indicating similarity
    """
    
    def __init__(self, csv_path: str, tokenizer, max_length: int = 512):
        """
        Initialize dataset
        
        Args:
            csv_path: Path to CSV file with address pairs and similarity scores
            tokenizer: Hugging Face tokenizer
            max_length: Maximum sequence length for tokenization
        """
        self.data = pd.read_csv(csv_path)
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Validate required columns
        required_cols = ['address_1', 'address_2', 'similarity_score']
        if not all(col in self.data.columns for col in required_cols):
            raise ValueError(f"CSV must contain columns: {required_cols}")
        
        # Clean and validate similarity scores
        self.data['similarity_score'] = pd.to_numeric(self.data['similarity_score'], errors='coerce')
        self.data = self.data.dropna()
        
        # Ensure similarity scores are between 0 and 1
        if not ((self.data['similarity_score'] >= 0) & (self.data['similarity_score'] <= 1)).all():
            logger.warning("Some similarity scores are outside [0,1] range. Clipping values.")
            self.data['similarity_score'] = self.data['similarity_score'].clip(0, 1)
        
        logger.info(f"Loaded {len(self.data)} address pairs")
        logger.info(f"Similarity score distribution: {self.data['similarity_score'].describe()}")
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        row = self.data.iloc[idx]
        
        # Tokenize both addresses
        addr1_tokens = self.tokenizer(
            row['address_1'],
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        addr2_tokens = self.tokenizer(
            row['address_2'],
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'addr1_input_ids': addr1_tokens['input_ids'].squeeze(),
            'addr1_attention_mask': addr1_tokens['attention_mask'].squeeze(),
            'addr2_input_ids': addr2_tokens['input_ids'].squeeze(),
            'addr2_attention_mask': addr2_tokens['attention_mask'].squeeze(),
            'similarity_score': torch.tensor(row['similarity_score'], dtype=torch.float32)
        }

class LoRAEmbeddingModel(nn.Module):
    """
    Embedding model with LoRA adaptation for similarity learning
    """
    
    def __init__(self, model_name: str, lora_config: LoraConfig):
        """
        Initialize LoRA embedding model
        
        Args:
            model_name: Name of the base embedding model
            lora_config: LoRA configuration
        """
        super().__init__()
        
        # Load base model
        self.base_model = AutoModel.from_pretrained(model_name)
        self.hidden_size = self.base_model.config.hidden_size
        
        # Apply LoRA
        self.model = get_peft_model(self.base_model, lora_config)
        
        # Similarity head
        self.similarity_head = nn.Sequential(
            nn.Linear(self.hidden_size * 3, 512),  # [emb1, emb2, |emb1-emb2|]
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 1),
            nn.Sigmoid()
        )
        
        logger.info(f"Initialized LoRA model with {self.count_parameters()} parameters")
        logger.info(f"Trainable parameters: {self.count_trainable_parameters()}")
    
    def count_parameters(self):
        """Count total parameters"""
        return sum(p.numel() for p in self.parameters())
    
    def count_trainable_parameters(self):
        """Count trainable parameters"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
    
    def get_embeddings(self, input_ids, attention_mask):
        """
        Get embeddings for input text
        
        Args:
            input_ids: Token IDs
            attention_mask: Attention mask
            
        Returns:
            Pooled embeddings
        """
        outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
        
        # Mean pooling
        token_embeddings = outputs.last_hidden_state
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
        
        # Normalize embeddings
        embeddings = F.normalize(embeddings, p=2, dim=1)
        
        return embeddings
    
    def forward(self, addr1_input_ids, addr1_attention_mask, addr2_input_ids, addr2_attention_mask):
        """
        Forward pass for similarity prediction
        
        Args:
            addr1_input_ids: First address token IDs
            addr1_attention_mask: First address attention mask
            addr2_input_ids: Second address token IDs
            addr2_attention_mask: Second address attention mask
            
        Returns:
            Predicted similarity score
        """
        # Get embeddings
        emb1 = self.get_embeddings(addr1_input_ids, addr1_attention_mask)
        emb2 = self.get_embeddings(addr2_input_ids, addr2_attention_mask)
        
        # Create feature vector: [emb1, emb2, |emb1-emb2|]
        diff = torch.abs(emb1 - emb2)
        features = torch.cat([emb1, emb2, diff], dim=1)
        
        # Predict similarity
        similarity = self.similarity_head(features)
        
        return similarity.squeeze()

class EmbeddingTrainer:
    """
    Trainer class for LoRA embedding fine-tuning
    """
    
    def __init__(self, config: TrainingConfig):
        """
        Initialize trainer
        
        Args:
            config: Training configuration
        """
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Initialize model
        lora_config = LoraConfig(
            task_type=TaskType.FEATURE_EXTRACTION,
            r=config.lora_r,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            target_modules=["query", "key", "value", "dense"]
        )
        
        self.model = LoRAEmbeddingModel(config.model_name, lora_config)
        self.model.to(self.device)
        
        # Initialize optimizer
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay
        )
        
        # Loss function
        self.criterion = nn.MSELoss()
        
        # Initialize wandb if requested
        if config.use_wandb:
            wandb.init(
                project=config.wandb_project,
                config=config.__dict__
            )
    
    def prepare_data(self, train_csv_path: str, val_csv_path: Optional[str] = None, test_size: float = 0.2):
        """
        Prepare training and validation datasets
        
        Args:
            train_csv_path: Path to training CSV
            val_csv_path: Optional path to validation CSV
            test_size: Fraction for train/val split if val_csv_path not provided
        """
        # Load training data
        train_dataset = AddressSimilarityDataset(train_csv_path, self.tokenizer, self.config.max_length)
        
        if val_csv_path:
            # Use separate validation file
            val_dataset = AddressSimilarityDataset(val_csv_path, self.tokenizer, self.config.max_length)
        else:
            # Split training data
            train_indices, val_indices = train_test_split(
                range(len(train_dataset)),
                test_size=test_size,
                random_state=42,
                stratify=pd.cut(train_dataset.data['similarity_score'], bins=5, labels=False)
            )
            
            train_data = train_dataset.data.iloc[train_indices].reset_index(drop=True)
            val_data = train_dataset.data.iloc[val_indices].reset_index(drop=True)
            
            # Create temporary CSV files for datasets
            train_data.to_csv('temp_train.csv', index=False)
            val_data.to_csv('temp_val.csv', index=False)
            
            train_dataset = AddressSimilarityDataset('temp_train.csv', self.tokenizer, self.config.max_length)
            val_dataset = AddressSimilarityDataset('temp_val.csv', self.tokenizer, self.config.max_length)
        
        # Create data loaders
        self.train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=4,
            pin_memory=True
        )
        
        self.val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
            shuffle=False,
            num_workers=4,
            pin_memory=True
        )
        
        # Initialize scheduler
        total_steps = len(self.train_loader) * self.config.num_epochs // self.config.gradient_accumulation_steps
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=self.config.warmup_steps,
            num_training_steps=total_steps
        )
        
        logger.info(f"Training samples: {len(train_dataset)}")
        logger.info(f"Validation samples: {len(val_dataset)}")
        logger.info(f"Total training steps: {total_steps}")
    
    def train_epoch(self):
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        num_batches = 0
        
        progress_bar = tqdm(self.train_loader, desc="Training")
        
        for step, batch in enumerate(progress_bar):
            # Move batch to device
            batch = {k: v.to(self.device) for k, v in batch.items()}
            
            # Forward pass
            predictions = self.model(
                batch['addr1_input_ids'],
                batch['addr1_attention_mask'],
                batch['addr2_input_ids'],
                batch['addr2_attention_mask']
            )
            
            loss = self.criterion(predictions, batch['similarity_score'])
            
            # Backward pass
            loss = loss / self.config.gradient_accumulation_steps
            loss.backward()
            
            if (step + 1) % self.config.gradient_accumulation_steps == 0:
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
                self.optimizer.step()
                self.scheduler.step()
                self.optimizer.zero_grad()
            
            total_loss += loss.item() * self.config.gradient_accumulation_steps
            num_batches += 1
            
            # Update progress bar
            progress_bar.set_postfix({'loss': loss.item() * self.config.gradient_accumulation_steps})
            
            # Log to wandb
            if self.config.use_wandb and step % 10 == 0:
                wandb.log({
                    'train_loss': loss.item() * self.config.gradient_accumulation_steps,
                    'learning_rate': self.scheduler.get_last_lr()[0]
                })
        
        return total_loss / num_batches
    
    def evaluate(self):
        """Evaluate on validation set"""
        self.model.eval()
        total_loss = 0
        predictions_list = []
        targets_list = []
        
        with torch.no_grad():
            for batch in tqdm(self.val_loader, desc="Evaluating"):
                batch = {k: v.to(self.device) for k, v in batch.items()}
                
                predictions = self.model(
                    batch['addr1_input_ids'],
                    batch['addr1_attention_mask'],
                    batch['addr2_input_ids'],
                    batch['addr2_attention_mask']
                )
                
                loss = self.criterion(predictions, batch['similarity_score'])
                total_loss += loss.item()
                
                predictions_list.extend(predictions.cpu().numpy())
                targets_list.extend(batch['similarity_score'].cpu().numpy())
        
        avg_loss = total_loss / len(self.val_loader)
        
        # Calculate metrics
        predictions_array = np.array(predictions_list)
        targets_array = np.array(targets_list)
        
        mae = np.mean(np.abs(predictions_array - targets_array))
        mse = np.mean((predictions_array - targets_array) ** 2)
        correlation = np.corrcoef(predictions_array, targets_array)[0, 1]
        
        metrics = {
            'val_loss': avg_loss,
            'val_mae': mae,
            'val_mse': mse,
            'val_correlation': correlation
        }
        
        return metrics
    
    def train(self, train_csv_path: str, val_csv_path: Optional[str] = None):
        """
        Main training loop
        
        Args:
            train_csv_path: Path to training CSV
            val_csv_path: Optional path to validation CSV
        """
        # Prepare data
        self.prepare_data(train_csv_path, val_csv_path)
        
        # Create output directory
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        best_val_loss = float('inf')
        
        for epoch in range(self.config.num_epochs):
            logger.info(f"Epoch {epoch + 1}/{self.config.num_epochs}")
            
            # Train
            train_loss = self.train_epoch()
            
            # Evaluate
            val_metrics = self.evaluate()
            
            logger.info(f"Train Loss: {train_loss:.4f}")
            logger.info(f"Val Loss: {val_metrics['val_loss']:.4f}")
            logger.info(f"Val MAE: {val_metrics['val_mae']:.4f}")
            logger.info(f"Val Correlation: {val_metrics['val_correlation']:.4f}")
            
            # Log to wandb
            if self.config.use_wandb:
                wandb.log({
                    'epoch': epoch + 1,
                    'train_loss': train_loss,
                    **val_metrics
                })
            
            # Save best model
            if val_metrics['val_loss'] < best_val_loss:
                best_val_loss = val_metrics['val_loss']
                self.save_model(f"{self.config.output_dir}/best_model")
                logger.info("Saved new best model")
        
        # Save final model
        self.save_model(f"{self.config.output_dir}/final_model")
        logger.info("Training completed!")
    
    def save_model(self, path: str):
        """Save model and tokenizer"""
        os.makedirs(path, exist_ok=True)
        
        # Save LoRA weights
        self.model.model.save_pretrained(path)
        
        # Save tokenizer
        self.tokenizer.save_pretrained(path)
        
        # Save config
        with open(f"{path}/training_config.json", 'w') as f:
            json.dump(self.config.__dict__, f, indent=2)
    
    def load_model(self, path: str):
        """Load trained model"""
        # Load LoRA config
        lora_config = LoraConfig.from_pretrained(path)
        
        # Recreate model
        self.model = LoRAEmbeddingModel(self.config.model_name, lora_config)
        self.model.model = self.model.model.from_pretrained(path)
        self.model.to(self.device)
        
        logger.info(f"Loaded model from {path}")

def main():
    """Example usage"""
    # Configuration
    config = TrainingConfig(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=16,
        learning_rate=2e-4,
        num_epochs=5,
        lora_r=16,
        lora_alpha=32,
        output_dir="./address_embedding_lora",
        use_wandb=False  # Set to True to enable wandb logging
    )
    
    # Initialize trainer
    trainer = EmbeddingTrainer(config)
    
    # Train model
    # trainer.train("path/to/your/address_dataset.csv")
    
    # Example of loading and using trained model
    # trainer.load_model("./address_embedding_lora/best_model")
    
    print("Training setup complete! Uncomment the train() call to start training.")

if __name__ == "__main__":
    main()
