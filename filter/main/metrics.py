"""
Evaluation Metrics Calculator
==============================
Calculate evaluation metrics for gibberish detection model.
Compares ground truth annotations with model predictions.

Ground truth: 'annotation' field ("yes" or "no" for gibberish)
Predictions: 'result.is_gibberish' field ("yes" or "no")
"""

# =============================================================================
#                           IMPORTS
# =============================================================================

import json
from pathlib import Path
from typing import List, Tuple, Dict, Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)

# =============================================================================
#                           CONFIGURATION PARAMETERS
# =============================================================================

DEFAULT_INPUT_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/results/label_studio_gibberish_results_new.jsonl"
DEFAULT_MISPREDICTIONS_FILE = "/Users/rishabh.singh/Desktop/markdown_filter/filter/results/mispredictions_new_2.json"

# =============================================================================
#                           DATA LOADING FUNCTIONS
# =============================================================================

def load_data(file_path: str) -> Tuple[List[str], List[str]]:
    """
    Load ground truth and predictions from JSONL file.
    
    Args:
        file_path: Path to JSONL file with annotations and results
    
    Returns:
        Tuple of (ground_truth, predictions) lists
    """
    ground_truth = []
    predictions = []
    skipped = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
                
            try:
                data = json.loads(line)
                
                # Get ground truth annotation
                annotation = data.get('annotation', '').strip()
                
                # Skip entries without annotations
                if not annotation:
                    skipped += 1
                    continue
                
                # Get model prediction
                prediction = data.get('result', {}).get('is_gibberish', '')
                
                if not prediction:
                    print(f"Warning: Line {line_num} has annotation but no prediction")
                    skipped += 1
                    continue
                
                # Validate values
                if annotation not in ['yes', 'no']:
                    print(f"Warning: Line {line_num} has invalid annotation: {annotation}")
                    skipped += 1
                    continue
                    
                if prediction not in ['yes', 'no']:
                    print(f"Warning: Line {line_num} has invalid prediction: {prediction}")
                    skipped += 1
                    continue
                
                ground_truth.append(annotation)
                predictions.append(prediction)
                
            except json.JSONDecodeError as e:
                print(f"Warning: Line {line_num} is not valid JSON: {e}")
                skipped += 1
                continue
    
    print(f"Loaded {len(ground_truth)} valid samples")
    if skipped > 0:
        print(f"Skipped {skipped} samples (missing/invalid annotations or predictions)")
    print()
    
    return ground_truth, predictions

# =============================================================================
#                           METRICS CALCULATION
# =============================================================================

def calculate_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
    """
    Calculate comprehensive evaluation metrics.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
    
    Returns:
        Dictionary containing all metrics
    """
    # Convert to binary (1 = gibberish/yes, 0 = useful/no)
    y_true_binary = [1 if label == 'yes' else 0 for label in y_true]
    y_pred_binary = [1 if label == 'yes' else 0 for label in y_pred]
    
    # Calculate metrics
    metrics = {
        'accuracy': accuracy_score(y_true_binary, y_pred_binary),
        
        # Binary metrics (for "yes" = gibberish = positive class)
        'precision_gibberish': precision_score(y_true_binary, y_pred_binary, pos_label=1),
        'recall_gibberish': recall_score(y_true_binary, y_pred_binary, pos_label=1),
        'f1_gibberish': f1_score(y_true_binary, y_pred_binary, pos_label=1),
        
        # Binary metrics (for "no" = useful = positive class)
        'precision_useful': precision_score(y_true_binary, y_pred_binary, pos_label=0),
        'recall_useful': recall_score(y_true_binary, y_pred_binary, pos_label=0),
        'f1_useful': f1_score(y_true_binary, y_pred_binary, pos_label=0),
        
        # Macro-averaged metrics (average of both classes)
        'precision_macro': precision_score(y_true_binary, y_pred_binary, average='macro'),
        'recall_macro': recall_score(y_true_binary, y_pred_binary, average='macro'),
        'f1_macro': f1_score(y_true_binary, y_pred_binary, average='macro'),
        
        # Weighted metrics (weighted by support)
        'precision_weighted': precision_score(y_true_binary, y_pred_binary, average='weighted'),
        'recall_weighted': recall_score(y_true_binary, y_pred_binary, average='weighted'),
        'f1_weighted': f1_score(y_true_binary, y_pred_binary, average='weighted'),
        
        # Confusion matrix
        'confusion_matrix': confusion_matrix(y_true_binary, y_pred_binary),
        
        # Class distribution
        'total_samples': len(y_true),
        'gibberish_true': sum(y_true_binary),
        'useful_true': len(y_true_binary) - sum(y_true_binary),
        'gibberish_pred': sum(y_pred_binary),
        'useful_pred': len(y_pred_binary) - sum(y_pred_binary),
    }
    
    return metrics

# =============================================================================
#                           REPORTING FUNCTIONS
# =============================================================================

def print_metrics(metrics: Dict[str, Any]):
    """
    Print metrics in a clean, formatted way.
    
    Args:
        metrics: Dictionary of calculated metrics
    """
    print("="*80)
    print("EVALUATION METRICS: Gibberish Detection Model")
    print("="*80)
    print()
    
    # Dataset statistics
    print("📊 Dataset Statistics")
    print("-" * 80)
    print(f"Total samples:              {metrics['total_samples']}")
    print(f"  Ground truth gibberish:   {metrics['gibberish_true']} ({metrics['gibberish_true']/metrics['total_samples']*100:.1f}%)")
    print(f"  Ground truth useful:      {metrics['useful_true']} ({metrics['useful_true']/metrics['total_samples']*100:.1f}%)")
    print(f"  Predicted gibberish:      {metrics['gibberish_pred']} ({metrics['gibberish_pred']/metrics['total_samples']*100:.1f}%)")
    print(f"  Predicted useful:         {metrics['useful_pred']} ({metrics['useful_pred']/metrics['total_samples']*100:.1f}%)")
    print()
    
    # Overall metrics
    print("🎯 Overall Performance")
    print("-" * 80)
    print(f"Accuracy:                   {metrics['accuracy']:.4f} ({metrics['accuracy']*100:.2f}%)")
    print()
    
    # Per-class metrics
    print("📈 Per-Class Metrics")
    print("-" * 80)
    print(f"{'Class':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12}")
    print("-" * 80)
    print(f"{'Gibberish (yes)':<20} {metrics['precision_gibberish']:<12.4f} {metrics['recall_gibberish']:<12.4f} {metrics['f1_gibberish']:<12.4f}")
    print(f"{'Useful (no)':<20} {metrics['precision_useful']:<12.4f} {metrics['recall_useful']:<12.4f} {metrics['f1_useful']:<12.4f}")
    print()
    
    # Confusion matrix
    print("🔢 Confusion Matrix")
    print("-" * 80)
    cm = metrics['confusion_matrix']
    print(f"                    Predicted:")
    print(f"                    Useful (no)   Gibberish (yes)")
    print(f"Actual:")
    print(f"  Useful (no)       {cm[0][0]:<14d} {cm[0][1]:<14d}")
    print(f"  Gibberish (yes)   {cm[1][0]:<14d} {cm[1][1]:<14d}")
    print()
    
    # Confusion matrix interpretation
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
    print("Interpretation:")
    print(f"  ✅ True Positives (TP):   {tp:4d} - Correctly identified gibberish")
    print(f"  ✅ True Negatives (TN):   {tn:4d} - Correctly identified useful")
    print(f"  ❌ False Positives (FP):  {fp:4d} - Useful pages marked as gibberish (Type I error)")
    print(f"  ❌ False Negatives (FN):  {fn:4d} - Gibberish pages marked as useful (Type II error)")
    print()
    
    print("="*80)


def print_sklearn_classification_report(y_true: List[str], y_pred: List[str]):
    """
    Print sklearn's built-in classification report.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
    """
    # Convert to binary
    y_true_binary = [1 if label == 'yes' else 0 for label in y_true]
    y_pred_binary = [1 if label == 'yes' else 0 for label in y_pred]
    
    print("\n" + "="*80)
    print("CLASSIFICATION REPORT")
    print("="*80)
    print()
    
    # Custom target names for better readability
    target_names = ['Useful (no)', 'Gibberish (yes)']
    
    report = classification_report(
        y_true_binary, 
        y_pred_binary,
        target_names=target_names,
        digits=4
    )
    print(report)
    print("="*80)

# =============================================================================
#                           MISPREDICTION STORAGE
# =============================================================================

def save_mispredictions(file_path: str, output_file: str):
    """
    Extract and save mispredicted results to JSON file.
    
    Args:
        file_path: Path to input JSONL file with annotations and results
        output_file: Path to output JSON file for mispredictions
    """
    mispredictions = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                data = json.loads(line)
                
                # Get ground truth and prediction
                annotation = data.get('annotation', '').strip()
                prediction = data.get('result', {}).get('is_gibberish', '').strip()
                
                # Skip if missing or invalid
                if not annotation or not prediction:
                    continue
                if annotation not in ['yes', 'no'] or prediction not in ['yes', 'no']:
                    continue
                
                # Check if mispredicted
                if annotation != prediction:
                    misprediction = {
                        'url': data.get('url', 'N/A'),
                        'title': data.get('title', 'N/A'),
                        'ground_truth': annotation,
                        'prediction': prediction,
                        'error_type': get_error_type(annotation, prediction)
                    }
                    mispredictions.append(misprediction)
                    
            except json.JSONDecodeError:
                continue
    
    # Save to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mispredictions, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved {len(mispredictions)} mispredictions to: {output_file}")
    
    return mispredictions


def get_error_type(ground_truth: str, prediction: str) -> str:
    """
    Determine the type of prediction error.
    
    Args:
        ground_truth: Actual label
        prediction: Predicted label
    
    Returns:
        Error type description
    """
    if ground_truth == 'no' and prediction == 'yes':
        return "False Positive (Useful marked as Gibberish)"
    elif ground_truth == 'yes' and prediction == 'no':
        return "False Negative (Gibberish marked as Useful)"
    else:
        return "Correct"

# =============================================================================
#                           MAIN EXECUTION
# =============================================================================

def main():
    """
    Main function to calculate and display metrics.
    """
    input_file = DEFAULT_INPUT_FILE
    mispredictions_file = DEFAULT_MISPREDICTIONS_FILE
    
    print(f"Loading data from: {input_file}\n")
    
    # Load data
    y_true, y_pred = load_data(input_file)
    
    if len(y_true) == 0:
        print("❌ Error: No valid samples found with both annotations and predictions")
        return
    
    # Calculate metrics
    metrics = calculate_metrics(y_true, y_pred)
    
    # Print metrics
    print_metrics(metrics)
    
    # Print sklearn classification report
    print_sklearn_classification_report(y_true, y_pred)
    
    # Save mispredictions
    mispredictions = save_mispredictions(input_file, mispredictions_file)


if __name__ == "__main__":
    main()
