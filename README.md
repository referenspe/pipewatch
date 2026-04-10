# pipewatch

A lightweight CLI tool for monitoring and alerting on data pipeline health metrics in real time.

---

## Installation

```bash
pip install pipewatch
```

Or install from source:

```bash
git clone https://github.com/yourname/pipewatch.git
cd pipewatch && pip install -e .
```

---

## Usage

Start monitoring a pipeline by pointing pipewatch at your metrics endpoint or log source:

```bash
pipewatch monitor --source kafka://localhost:9092 --topic pipeline-metrics
```

Set alert thresholds and get notified when something goes wrong:

```bash
pipewatch monitor --source ./pipeline.log --alert-on error_rate>0.05 --alert-on lag>1000
```

Watch a live dashboard in your terminal:

```bash
pipewatch dashboard --refresh 5
```

### Common Options

| Flag | Description |
|------|-------------|
| `--source` | Metrics source (file, Kafka, HTTP endpoint) |
| `--alert-on` | Alert rule in `metric>threshold` format |
| `--refresh` | Dashboard refresh interval in seconds |
| `--output` | Output format: `text`, `json`, or `csv` |

---

## Requirements

- Python 3.8+
- Works on Linux, macOS, and Windows

---

## License

This project is licensed under the [MIT License](LICENSE).