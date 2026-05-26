Generated ML preparation artifacts are written here.

Rebuild from `simulation/`:

```bash
python3 ml/prepare_data.py
```

Expected generated files:

- `prepared_training_data.csv`
- `prepared_training_data_base.csv`
- `prepared_training_data_alt_1.csv`
- `data_summary.json`

The trained model artifact is not stored in this directory. It is written by
`python3 ml/train.py` to:

- `simulation/ml/model_coefficients.json`
