document.addEventListener("DOMContentLoaded", function() {
    // Theme loading
    const savedTheme = localStorage.getItem('app_theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
        const themeSelector = document.getElementById('themeSelector');
        if (themeSelector) themeSelector.value = savedTheme;
    }
});

function changeTheme(selectObject) {
    const theme = selectObject.value;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('app_theme', theme);
}

// Joyous Tune Synthesis
function playCompletionTune() {
    if (!window.AudioContext && !window.webkitAudioContext) return;
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    function playNote(freq, startTime, duration) {
        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime + startTime);
        
        gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime + startTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + startTime + duration);
        
        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        osc.start(audioCtx.currentTime + startTime);
        osc.stop(audioCtx.currentTime + startTime + duration);
    }
    
    // C Major Arpeggio (Joyous!)
    playNote(523.25, 0.0, 0.1); // C5
    playNote(659.25, 0.1, 0.1); // E5
    playNote(783.99, 0.2, 0.1); // G5
    playNote(1046.50, 0.3, 0.3); // C6
}

function completeTask(href) {
    // Play tune then redirect
    playCompletionTune();
    setTimeout(() => {
        window.location.href = href;
    }, 450); // give enough time for sound to play
    return false;
}
