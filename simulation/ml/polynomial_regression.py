"""
Polynomial Regression (degree-2) — built on top of the from-scratch
LinearRegression class by adding squared feature terms before fitting.

No external ML libraries are used.

Usage:
    from ml.polynomial_regression import PolynomialRegression

    model = PolynomialRegression()
    model.fit(X_train, y_train, learning_rate=0.01, iterations=1000)
    y_pred = model.predict(x)
"""

from ml.linear_regression import LinearRegression


class PolynomialRegression(LinearRegression):
    """Degree-2 polynomial regression via feature expansion.

    For an input vector x = [x1, x2, …, xk], the expanded vector is:
        x_exp = [x1, x2, …, xk,  x1², x2², …, xk²]

    This doubles the number of parameters and allows the model to capture
    non-linear (quadratic) relationships between features and target.

    All fitting and prediction is delegated to the parent LinearRegression
    using the expanded feature space.
    """

    @staticmethod
    def _expand(x):
        """Append squared terms: [x1,..,xk] → [x1,..,xk, x1²,..,xk²]."""
        return list(x) + [xi ** 2 for xi in x]

    def fit(self, X, y, **kwargs):
        """Expand features then delegate to LinearRegression.fit()."""
        X_exp = [self._expand(x) for x in X]
        return super().fit(X_exp, y, **kwargs)

    def predict(self, x):
        """Predict for a single (un-expanded) feature vector."""
        return super().predict(self._expand(x))

    def predict_batch(self, X):
        return [self.predict(x) for x in X]

    def mse(self, X, y):
        return super().mse([self._expand(x) for x in X], y)

    def mae(self, X, y):
        return super().mae([self._expand(x) for x in X], y)

    def r2(self, X, y):
        return super().r2([self._expand(x) for x in X], y)

    def rmse(self, X, y):
        return super().rmse([self._expand(x) for x in X], y)
