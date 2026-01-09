# ChartChampion AI

ChartChampion AI is a tool for analyzing and visualizing crypto market data processed and analized by an AI agent to make decisions in the market following Chat Champion trading strategy.

# How this project was created

1. Install Whisper.cpp to transcribe audio files to text.

In the terminal, install by running:

    git clone https://github.com/ggml-org/whisper.cpp.git
    cd whisper.cpp
    sh ./models/download-ggml-model.sh base.en

Transcribe audio file to text:

    # build the project
    cmake -B build
    cmake --build build -j --config Release
    # transcribe an audio file
    ./build/bin/whisper-cli -f samples/jfk.wav

You can also run something like this (according to the terminal output):

    ./build/bin/whisper-cli -m /Users/famalam/code/chartchampionAI/whisper.cpp/models/ggml-base.en.bin -f samples/jfk.wav

2. Install FFmpeg to convert audio files to wav format.

In the terminal, install by running:

    brew install ffmpeg

Convert audio file to wav format:

    ffmpeg -i input.mp3 output.wav

Or run:

    ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav

Or run:

    ffmpeg -i your_video.mp4 -vn -acodec pcm_s16le output.wav