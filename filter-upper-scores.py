def filter_scores(scores, threshold_ratio=5):
    """
    Filters out significantly lower scores from a list of scores.

    Parameters:
    scores (list of float): The input list of scores.
    threshold_ratio (float): The ratio used to determine a significant gap.

    Returns:
    list of float: The filtered list of scores.
    """
    # Sort the scores in descending order
    sorted_scores = sorted(scores, reverse=True)

    # Compute the differences between adjacent scores
    differences = [sorted_scores[i] - sorted_scores[i + 1] for i in range(len(sorted_scores) - 1)]

    # Find the maximum difference and its index
    max_diff = max(differences)
    max_diff_index = differences.index(max_diff)

    # Compute the mean of differences excluding the maximum difference
    differences_excluding_max = differences[:max_diff_index] + differences[max_diff_index + 1:]
    mean_diff = sum(differences_excluding_max) / len(differences_excluding_max) if differences_excluding_max else 0

    # Check if the maximum difference is significantly larger than the mean of other differences
    if mean_diff > 0 and max_diff > threshold_ratio * mean_diff:
        # Filter out the scores below the significant gap
        filtered_scores = sorted_scores[:max_diff_index + 1]
    else:
        # Return the distribution unchanged
        filtered_scores = scores

    return filtered_scores

# Example usage with the provided scores
scores_1 = [285.47742, 282.72930, 279.94778, 274.34866, 271.43427, 269.50778,
            268.62130, 259.50742, 259.50742, 258.95557, 257.76605, 257.72354,
            257.51202, 257.36722, 257.09660, 256.58536, 242.26219, 228.02120,
            92.02120, 90.4412]
filtered_scores_1 = filter_scores(scores_1)
print("Filtered scores_1:", filtered_scores_1)

scores_2 = [142.130680, 141.431670, 119.087524, 119.075700, 117.050995,
            21.869064, 8.985836, 8.980824, 8.980664, 8.979238, 8.979018,
            8.975421, 8.974961, 8.973046, 8.969814, 8.966190, 8.964828,
            0.725726, 0.700161, 0.697418]
filtered_scores_2 = filter_scores(scores_2)
print("Filtered scores_2:", filtered_scores_2)

scores_3 = [343.20248, 334.50937, 334.04077, 325.34286, 325.19748, 324.85184,
            323.05023, 322.77914, 321.92460, 321.82010, 321.46533, 320.46146,
            319.68558, 319.59920, 318.93448, 318.48914, 317.98883, 317.30658,
            317.24320, 316.8812]
filtered_scores_3 = filter_scores(scores_3)
print("Filtered scores_3:", filtered_scores_3)