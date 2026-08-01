<#
.SYNOPSIS
    Interactive helper to pull an Ollama model and/or pre-download a
    faster-whisper model into the Docker volume, using the profiles from
    the README.
#>

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== Download local models ===" -ForegroundColor Cyan

# --- Ollama (QA scoring LLM) ---
Write-Host "`n-- Ollama model (QA scoring) --"
Write-Host "faster-whisper downloads its model automatically on first use, but"
Write-Host "Ollama models must be pulled explicitly."
Write-Host ""
Write-Host "  1) qwen2.5:3b   - CPU / low-spec, lower QA quality"
Write-Host "  2) qwen2.5:7b   - CPU recommended / GPU 6-8 GB (default in .env.example)"
Write-Host "  3) qwen2.5:14b  - GPU 12 GB+, better QA quality"
Write-Host "  4) custom model name"
Write-Host "  0) skip"

$choice = Read-Host "Choose an option"
$ollamaModel = $null
switch ($choice) {
    "1" { $ollamaModel = "qwen2.5:3b" }
    "2" { $ollamaModel = "qwen2.5:7b" }
    "3" { $ollamaModel = "qwen2.5:14b" }
    "4" { $ollamaModel = Read-Host "Enter the Ollama model name (e.g. llama3.1:8b)" }
    default { Write-Host "Skipping Ollama model download." }
}

if ($ollamaModel) {
    if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
        Write-Host "[MISSING] ollama not found on PATH - install it first: https://ollama.com/download" -ForegroundColor Red
    } else {
        Write-Host "Running: ollama pull $ollamaModel"
        ollama pull $ollamaModel
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] pulled $ollamaModel" -ForegroundColor Green
            Write-Host "     Set LOCAL_LLM_MODEL=$ollamaModel in .env if this isn't the current default."
        } else {
            Write-Host "ollama pull failed - see output above." -ForegroundColor Red
        }
    }
}

# --- faster-whisper (transcription) ---
Write-Host "`n-- faster-whisper model (transcription) --"
Write-Host "This downloads automatically the first time a call is transcribed."
Write-Host "You can optionally pre-warm it now so the first real call isn't slow."
Write-Host ""
Write-Host "  1) tiny"
Write-Host "  2) base"
Write-Host "  3) small   - default (WHISPER_MODEL in .env.example)"
Write-Host "  4) medium"
Write-Host "  5) large-v3"
Write-Host "  0) skip"

$whisperChoice = Read-Host "Choose an option"
$whisperModel = $null
switch ($whisperChoice) {
    "1" { $whisperModel = "tiny" }
    "2" { $whisperModel = "base" }
    "3" { $whisperModel = "small" }
    "4" { $whisperModel = "medium" }
    "5" { $whisperModel = "large-v3" }
    default { Write-Host "Skipping faster-whisper pre-download." }
}

if ($whisperModel) {
    $containers = docker compose ps -q api 2>$null
    if (-not $containers) {
        Write-Host "The 'api' container isn't running - start it first with .\scripts\start.ps1" -ForegroundColor Red
    } else {
        Write-Host "Pre-downloading faster-whisper model '$whisperModel' into the api container..."
        docker compose exec -T api python -c "from faster_whisper import WhisperModel; WhisperModel('$whisperModel'); print('downloaded')"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] pre-downloaded $whisperModel" -ForegroundColor Green
            Write-Host "     Set WHISPER_MODEL=$whisperModel in .env if this isn't the current default."
        } else {
            Write-Host "Pre-download failed - see output above." -ForegroundColor Red
        }
    }
}

# --- sherpa-onnx diarization models (speaker labels for mono recordings) ---
Write-Host "`n-- Diarization models (speaker labels for mono/mp3 recordings) --"
Write-Host "Stereo WAV calls are labeled by channel and don't need these."
Write-Host "~90 MB total, downloaded once into the diarization_models volume."
Write-Host ""
Write-Host "  1) download"
Write-Host "  0) skip"

$diarChoice = Read-Host "Choose an option"
if ($diarChoice -eq "1") {
    $containers = docker compose ps -q api 2>$null
    if (-not $containers) {
        Write-Host "The 'api' container isn't running - start it first with .\scripts\start.ps1" -ForegroundColor Red
    } else {
        Write-Host "Downloading segmentation + embedding models into the api container..."
        $diarScript = @'
import tarfile
import urllib.request
from pathlib import Path

MODELS_DIR = Path("/models/diarization")
SEGMENTATION_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
    "speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
)
EMBEDDING_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/"
    "speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
)

MODELS_DIR.mkdir(parents=True, exist_ok=True)

seg_target = MODELS_DIR / "segmentation.onnx"
if seg_target.exists():
    print("segmentation.onnx already present - skipping")
else:
    archive = MODELS_DIR / "segmentation.tar.bz2"
    print("downloading", SEGMENTATION_URL)
    urllib.request.urlretrieve(SEGMENTATION_URL, archive)
    with tarfile.open(archive, "r:bz2") as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith("model.onnx"))
        member.name = seg_target.name
        tar.extract(member, MODELS_DIR)
    archive.unlink()
    print("saved", seg_target)

emb_target = MODELS_DIR / "embedding.onnx"
if emb_target.exists():
    print("embedding.onnx already present - skipping")
else:
    print("downloading", EMBEDDING_URL)
    urllib.request.urlretrieve(EMBEDDING_URL, emb_target)
    print("saved", emb_target)
'@
        $diarScript | docker compose exec -T api python -
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] diarization models ready" -ForegroundColor Green
        } else {
            Write-Host "Diarization model download failed - see output above." -ForegroundColor Red
        }
    }
} else {
    Write-Host "Skipping diarization models."
}

Write-Host "`nDone."
