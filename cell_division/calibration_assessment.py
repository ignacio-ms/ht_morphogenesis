from sklearn.calibration import calibration_curve
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import brier_score_loss
import tensorflow as tf


def plot_multilabel_reliability_diagram(y_true, y_pred, class_names, n_bins=10, sub_index=None, nrows=1, ncols=2):
    if sub_index:
        plt.subplot(nrows, ncols, sub_index)
    else:
        plt.figure(figsize=(5, 5))

    num_classes = y_pred.shape[1]

    for i in range(num_classes):
        prob_true, prob_pred = calibration_curve(y_true[:, i], y_pred[:, i], n_bins=n_bins)
        plt.plot(prob_pred, prob_true, marker='o', label=f'{class_names[i]}')
    plt.plot([0, 1], [0, 1], linestyle='--', color='gray')
    plt.xlabel('Mean Predicted Probability')
    plt.ylabel('Fraction of Positives')
    plt.title('Multilabel Reliability Diagram')
    plt.legend()
    plt.tight_layout()


def compute_ece(y_true, y_pred, n_bins=15):
    """
    Computes the Expected Calibration Error (ECE) for multiclass classification.

    Parameters:
    - y_true: True labels (numpy array), shape (n_samples,)
    - y_pred: Predicted probabilities (numpy array), shape (n_samples, n_classes)
    - n_bins: Number of bins to use in the computation.

    Returns:
    - ece: The Expected Calibration Error.
    """
    # Convert true labels to integer indices if necessary
    if y_true.ndim > 1:
        y_true = np.argmax(y_true, axis=1)

    # Get predicted class and confidence
    predicted_class = np.argmax(y_pred, axis=1)
    confidence = np.max(y_pred, axis=1)

    # Initialize variables
    ece = 0.0
    bin_size = 1.0 / n_bins

    for bin_lower in np.linspace(0.0, 1.0 - bin_size, n_bins):
        bin_upper = bin_lower + bin_size
        # Select samples where confidence is within the bin range
        bin_mask = (confidence > bin_lower) & (confidence <= bin_upper)
        bin_count = np.sum(bin_mask)

        if bin_count > 0:
            # Compute average confidence and accuracy in the bin
            bin_confidence = np.mean(confidence[bin_mask])
            bin_accuracy = np.mean(predicted_class[bin_mask] == y_true[bin_mask])

            # Compute weighted difference
            ece += (bin_count / y_true.shape[0]) * np.abs(bin_accuracy - bin_confidence)

    return ece


def plot_calibration_map(model, model_calibrated, X, y, title, sub_index=None, nrows=1, ncols=2):
    if sub_index:
        plt.subplot(nrows, ncols, sub_index)
    else:
        plt.figure(figsize=(5, 5))

    colors = ['r', 'g', 'b']
    y = [int(label) for label in y]

    probs = model.predict(X)
    probs_calibrated = model_calibrated.predict(X)

    plt.plot([0, 1, 0, 0], [0, 0, 1, 0], 'k')
    plt.plot([1], [0], 'ro', ms=10, label='Prophase/Metaphase')
    plt.plot([0], [1], 'go', ms=10, label='Anaphase/Telophase')
    plt.plot([0], [0], 'bo', ms=10, label='Interphase')

    for i in range(probs.shape[0]):
        plt.arrow(
            probs[i, 0], probs[i, 1],
            probs_calibrated[i, 0] - probs[i, 0], probs_calibrated[i, 1] - probs[i, 1],
            head_width=.01, color=colors[y[i] - 1]
        )

    plt.grid(False)
    for x in np.arange(0, 1, .1):
        plt.plot([0, x], [x, 0], "k", alpha=0.2)
        plt.plot([0, 0 + (1 - x) / 2], [x, x + (1 - x) / 2], "k", alpha=0.2)
        plt.plot([x, x + (1 - x) / 2], [0, 0 + (1 - x) / 2], "k", alpha=0.2)

    plt.title(title)
    plt.xlabel('Probability of Prophase/Metaphase')
    plt.ylabel('Probability of Anaphase/Telophase')
    plt.legend(loc='upper right')
    plt.tight_layout()


def plot_learned_calibration_map(model_calibrated, title, sub_index=None, nrows=1, ncols=2):
    if sub_index:
        plt.subplot(nrows, ncols, sub_index)
    else:
        plt.figure(figsize=(5, 5))

    def safe_log_tf(p):
        p = tf.clip_by_value(p, 1e-10, 1.0)
        return tf.math.log(p)

    colors = ['r', 'g', 'b']

    x0, x1 = np.meshgrid(
        np.linspace(0, 1, 20),
        np.linspace(0, 1, 20)
    )
    x2 = 1 - x0 - x1

    p = np.c_[x0.ravel(), x1.ravel(), x2.ravel()]
    p = p[p[:, 2] >= 0]

    p_logits = safe_log_tf(p)

    calibration_layers = []
    input_found = False
    for layer in model_calibrated.layers:
        if layer.name in ['temperature_scaling', 'vector_scaling', 'matrix_scaling', 'dirichlet_calibration']:
            calibration_layers.append(layer)
            input_found = True
        elif input_found:
            calibration_layers.append(layer)

    logits_input = tf.keras.Input(shape=(3,), name='logits_input')
    x = logits_input
    for layer in calibration_layers:
        x = layer(x)

    calibration_model = tf.keras.Model(inputs=logits_input, outputs=x)
    predictions = calibration_model.predict(p_logits)
    predictions /= predictions.sum(axis=1, keepdims=True)

    plt.plot([0, 1, 0, 0], [0, 0, 1, 0], 'k')
    plt.plot([1], [0], 'ro', ms=10, label='Prophase/Metaphase')
    plt.plot([0], [1], 'go', ms=10, label='Anaphase/Telophase')
    plt.plot([0], [0], 'bo', ms=10, label='Interphase')

    for i in range(p.shape[0]):
        plt.arrow(
            p[i, 0], p[i, 1],
            predictions[i, 0] - p[i, 0], predictions[i, 1] - p[i, 1],
            head_width=.01, color=colors[np.argmax(predictions[i])]
        )

    plt.grid(False)
    for x in np.arange(0, 1, .1):
        plt.plot([0, x], [x, 0], "k", alpha=0.2)
        plt.plot([0, 0 + (1 - x) / 2], [x, x + (1 - x) / 2], "k", alpha=0.2)
        plt.plot([x, x + (1 - x) / 2], [0, 0 + (1 - x) / 2], "k", alpha=0.2)

    plt.title(title)
    plt.xlabel('Probability of Prophase/Metaphase')
    plt.ylabel('Probability of Anaphase/Telophase')
    plt.legend(loc='upper right')
    plt.tight_layout()


def compute_multilabel_brier(y_true, y_pred):
    num_classes = y_true.shape[1]
    brier_scores = []

    for i in range(num_classes):
        bs = brier_score_loss(y_true[:, i], y_pred[:, i])
        brier_scores.append(bs)

    mean_brier_score = np.mean(brier_scores)
    return mean_brier_score