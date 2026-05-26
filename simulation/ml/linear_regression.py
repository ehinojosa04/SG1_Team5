"""
Linear Regression — implemented from scratch using pure Python.

No external ML libraries are used. Only the Python standard library (math).

Algorithm: batch gradient descent minimising Mean Squared Error.

Usage:
    from ml.linear_regression import LinearRegression

    model = LinearRegression()
    model.fit(X_train, y_train, learning_rate=0.05, iterations=1000)
    y_pred = model.predict(x)          # single sample
    r2     = model.r2(X_test, y_test)  # evaluation
"""

import math


class LinearRegression:
    """Ordinary least-squares linear regression via batch gradient descent.

    Attributes
    ----------
    weights : list[float]
        One coefficient per feature, learned during fit().
    bias : float
        Intercept term, learned during fit().
    loss_history : list[float]
        MSE recorded every 'log_every' epochs (for convergence plots).
    """

    def __init__(self):
        self.weights     = []
        self.bias        = 0.0
        self.loss_history = []

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, X, y, learning_rate=0.05, iterations=1000,
            log_every=100, verbose=True):
        """Train the model using batch gradient descent.

        Parameters
        ----------
        X : list[list[float]]  — shape (n_samples, n_features)
        y : list[float]        — shape (n_samples,)
        learning_rate : float  — step size for weight updates
        iterations : int       — number of full passes over the training data
        log_every : int        — print/record MSE every this many epochs
        verbose : bool         — print progress to stdout
        """
        n = len(X)
        k = len(X[0])
        self.weights  = [0.0] * k
        self.bias     = 0.0
        self.loss_history = []

        for epoch in range(iterations):
            # Forward pass – compute predictions
            preds  = [self._dot(X[i]) for i in range(n)]
            errors = [preds[i] - y[i]  for i in range(n)]

            # Gradients (mean over all samples)
            dw = [
                sum(errors[i] * X[i][j] for i in range(n)) / n
                for j in range(k)
            ]
            db = sum(errors) / n

            # Parameter update
            self.weights = [self.weights[j] - learning_rate * dw[j]
                            for j in range(k)]
            self.bias   -= learning_rate * db

            # Logging
            if epoch % log_every == 0 or epoch == iterations - 1:
                mse = sum(e ** 2 for e in errors) / n
                self.loss_history.append(mse)
                if verbose:
                    print(f"  epoch {epoch:>5d}/{iterations}  MSE: {mse:.6f}")

        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def _dot(self, x):
        """Compute w·x + b for a single sample x."""
        return self.bias + sum(self.weights[j] * x[j]
                               for j in range(len(self.weights)))

    def predict(self, x):
        """Return the scalar prediction for a single feature vector x."""
        return self._dot(x)

    def predict_batch(self, X):
        """Return predictions for all rows in X."""
        return [self._dot(x) for x in X]

    # ------------------------------------------------------------------
    # Evaluation metrics
    # ------------------------------------------------------------------

    def mse(self, X, y):
        """Mean Squared Error on dataset (X, y)."""
        preds = self.predict_batch(X)
        return sum((preds[i] - y[i]) ** 2 for i in range(len(y))) / len(y)

    def mae(self, X, y):
        """Mean Absolute Error on dataset (X, y)."""
        preds = self.predict_batch(X)
        return sum(abs(preds[i] - y[i]) for i in range(len(y))) / len(y)

    def r2(self, X, y):
        """Coefficient of determination R² on dataset (X, y).

        R² = 1 - SS_res / SS_tot.  Returns 0.0 if y is constant.
        """
        preds  = self.predict_batch(X)
        mean_y = sum(y) / len(y)
        ss_res = sum((y[i] - preds[i]) ** 2 for i in range(len(y)))
        ss_tot = sum((y[i] - mean_y)   ** 2 for i in range(len(y)))
        return 1.0 - ss_res / ss_tot if ss_tot != 0.0 else 0.0

    def rmse(self, X, y):
        """Root Mean Squared Error."""
        return math.sqrt(self.mse(X, y))
