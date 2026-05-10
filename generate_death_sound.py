def init_audio():
    global audio_ctx, bg_music, lowpass_filter
    try:
        audio_ctx = js.AudioContext.new()
        bg_music = js.Audio.new("music.mp3")
        bg_music.loop = True
        
        source = audio_ctx.createMediaElementSource(bg_music)
        lowpass_filter = audio_ctx.createBiquadFilter()
        lowpass_filter.type = "lowpass"
        
        # Ešte nižšia frekvencia (150Hz namiesto 300Hz) pre extrémne rozostrenie
        lowpass_filter.frequency.value = 150 
        # Pridanie resonancie (zvuk bude viac "tupý" a skreslený)
        lowpass_filter.Q.value = 10 
        
        source.connect(lowpass_filter)
        lowpass_filter.connect(audio_ctx.destination)
        bg_music.play()
    except Exception as e:
        print(f"Audio error: {e}")