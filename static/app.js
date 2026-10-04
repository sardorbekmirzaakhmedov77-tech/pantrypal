// The app's planning forms work without JavaScript. These are cooking enhancements.
const storage = {
  get(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } },
  set(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch {} }
};
document.querySelectorAll('.print-button').forEach(button => button.addEventListener('click', () => window.print()));
document.querySelectorAll('.search-bar').forEach(form => form.addEventListener('submit', () => {
  const button = form.querySelector('button'); button.dataset.label = button.textContent; button.textContent = 'Searching…'; button.disabled = true;
}));
window.addEventListener('pageshow', () => document.querySelectorAll('button[data-label]').forEach(b => { b.textContent = b.dataset.label; b.disabled = false; }));
const steps = document.querySelector('[data-cook-key]');
if (steps) {
  const key = 'pantrypal-steps-' + steps.dataset.cookKey;
  const inputs = [...steps.querySelectorAll('[data-step]')];
  const remembered = storage.get(key, []);
  inputs.forEach(input => { input.checked = Array.isArray(remembered) && remembered.includes(input.dataset.step); });
  const update = () => {
    const checked = inputs.filter(input => input.checked).map(input => input.dataset.step);
    storage.set(key, checked);
    document.getElementById('step-count').textContent = `${checked.length} / ${inputs.length} sections done`;
    document.getElementById('step-bar').style.width = `${inputs.length ? checked.length / inputs.length * 100 : 0}%`;
    document.getElementById('cook-complete').hidden = !inputs.length || checked.length !== inputs.length;
  };
  inputs.forEach(input => input.addEventListener('change', update));
  document.getElementById('reset-steps').addEventListener('click', () => { inputs.forEach(i => { i.checked = false; }); update(); });
  update();
}
const timer = document.querySelector('[data-timer-key]');
if (timer) {
  const key = 'pantrypal-timer-' + timer.dataset.timerKey;
  const display = document.getElementById('timer-display');
  const minutes = document.getElementById('timer-minutes');
  const start = document.getElementById('timer-start');
  const status = document.getElementById('timer-status');
  let state = storage.get(key, { end: null, remaining: 600000, started: false });
  if (!state || typeof state.remaining !== 'number' || state.remaining < 0 || state.remaining > 14400000 || (state.end !== null && !Number.isFinite(state.end))) state = { end: null, remaining: 600000, started: false };
  let audioContext = null;
  const save = () => storage.set(key, state);
  const render = () => {
    const ms = state.end ? Math.max(0, state.end - Date.now()) : state.remaining;
    const sec = Math.ceil(ms / 1000);
    display.textContent = `${String(Math.floor(sec / 60)).padStart(2,'0')}:${String(sec % 60).padStart(2,'0')}`;
    start.textContent = state.end ? 'Pause timer' : state.started && state.remaining > 0 ? 'Resume timer' : 'Start timer';
    minutes.disabled = state.started;
    if (state.end && ms === 0) {
      state = { end: null, remaining: 0, started: true }; save();
      status.textContent = 'Time is up! Check your food and follow the recipe.';
      if (audioContext) {
        const tone = audioContext.createOscillator(); const volume = audioContext.createGain();
        tone.connect(volume); volume.connect(audioContext.destination); tone.frequency.value = 660;
        volume.gain.setValueAtTime(0.12, audioContext.currentTime); volume.gain.exponentialRampToValueAtTime(0.001,audioContext.currentTime+0.8);
        tone.start(); tone.stop(audioContext.currentTime+0.8);
      }
    }
  };
  start.addEventListener('click', () => {
    if (state.end) {
      state.remaining = Math.max(0,state.end-Date.now()); state.end = null; status.textContent = 'Timer paused.';
    } else {
      if (!state.started || state.remaining === 0) {
        const n = Number(minutes.value);
        if (!Number.isInteger(n) || n < 1 || n > 240) { status.textContent = 'Choose 1–240 whole minutes.'; return; }
        state.remaining = n*60000;
      }
      state.end = Date.now()+state.remaining; state.started = true;
      status.textContent = 'Timer running. Keep this tab open for the alert.';
      try { audioContext ||= new (window.AudioContext || window.webkitAudioContext)(); audioContext.resume(); } catch {}
    }
    save(); render();
  });
  document.getElementById('timer-reset').addEventListener('click', () => {
    const n = Number(minutes.value); const valid = Number.isInteger(n) && n>=1 && n<=240 ? n : 10;
    minutes.value = valid; state = { end: null, remaining:valid*60000, started:false }; save(); status.textContent = 'Timer reset. Set your own time from the recipe.'; render();
  });
  if (state.end) status.textContent = 'Your timer is running. Keep this tab open.';
  else if (state.started && state.remaining === 0) status.textContent = 'Your previous timer finished.';
  else if (state.started) status.textContent = 'Your timer is paused.';
  render(); setInterval(render,250);
}
