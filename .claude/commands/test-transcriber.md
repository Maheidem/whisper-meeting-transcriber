---
allowed-tools: Bash, Read, Glob
description: Test the Meeting Transcriber with deterministic validation
---

Run comprehensive tests on the Meeting Transcriber application to validate functionality.

## Test Data

Test file: `test_data/test_10min.mp4` (10-minute extract from meeting recording)

## Pre-flight Checks

1. **Verify test file exists**: Check `test_data/test_10min.mp4` exists
2. **Check server not running**: `netstat -ano | findstr :8000` should be empty
3. **Verify PyTorch CUDA**: Run Python check for torch.cuda.is_available()

## Test Suite

### Test 1: Basic Transcription (No Diarization)

**Purpose**: Validate core transcription works with GPU acceleration

```bash
cd C:/Users/mahei/Documents/whisper-meeting-transcriber
./venv/Scripts/python.exe cli.py test_data/test_10min.mp4 -m base -l pt -f txt
```

**Expected**:
- Exit code 0
- Output file created in `results/` directory
- Log shows "Model loaded on CUDA"
- Transcription completes in < 60 seconds for 10-min file

**Validation**:
- Check result file exists and has content
- Verify file size > 1KB (not empty)
- Parse transcription time from logs

### Test 2: Transcription with GPU Diarization

**Purpose**: Validate diarization works on CUDA (RTX 5090 with PyTorch cu128)

```bash
cd C:/Users/mahei/Documents/whisper-meeting-transcriber
./venv/Scripts/python.exe cli.py test_data/test_10min.mp4 -m base -l pt -f txt --diarize --min-speakers 2 --max-speakers 4
```

**Expected**:
- Exit code 0
- Log shows "Diarization will use CUDA (NVIDIA GeForce RTX 5090)"
- Log shows "Diarization pipeline loaded" with device=cuda
- Speakers detected > 0
- Diarization completes in < 2 minutes for 10-min file

**Validation**:
- Check result file contains speaker labels `[SPEAKER_XX]`
- Verify speakers_detected in logs is > 0
- Confirm GPU was used (not CPU fallback)

### Test 3: Web API Test

**Purpose**: Validate FastAPI server and endpoints

1. Start server in background:
   ```bash
   ./venv/Scripts/python.exe app.py &
   ```

2. Wait for startup (5 seconds)

3. Test endpoints:
   ```bash
   curl -s http://localhost:8000/health
   curl -s http://localhost:8000/gpu
   curl -s http://localhost:8000/models
   ```

4. Stop server

**Expected**:
- `/health` returns 200
- `/gpu` shows `cuda` backend with RTX 5090
- `/models` lists available models

### Test 4: Output Format Validation

**Purpose**: Validate all output formats work correctly

For each format (txt, srt, vtt, json, tsv):
```bash
./venv/Scripts/python.exe cli.py test_data/test_10min.mp4 -m tiny -l pt -f {format}
```

**Expected**:
- All formats produce valid output
- SRT has proper timestamp format (HH:MM:SS,mmm)
- VTT has WEBVTT header
- JSON is valid JSON with segments array
- TSV has header row

## Performance Benchmarks

Track these metrics for regression testing:

| Metric | Expected | Actual |
|--------|----------|--------|
| Model load time (base) | < 10s | |
| Transcription speed (10min, base) | < 60s | |
| Diarization speed (10min, GPU) | < 120s | |
| Memory usage (peak) | < 8GB | |

## Cleanup

After tests:
1. Delete test result files from `results/`
2. Stop any running server processes
3. Report summary

## Success Criteria

All tests pass when:
- [x] Basic transcription works with CUDA
- [x] Diarization uses GPU (not CPU fallback)
- [x] Speaker labels appear in output
- [x] All output formats valid
- [x] Performance within expected bounds

## Error Handling

If tests fail:
1. Check server logs in `logs/transcriber.log`
2. Verify PyTorch CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
3. Check GPU memory: `nvidia-smi`
4. Report specific failure with error message
