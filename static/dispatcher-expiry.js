/* No new location reads or third-party requests. Expire already rendered coordinates
   even without refresh. Check when a suspended tab becomes visible again. */
(() => {
  const panel = document.getElementById('location-panel');
  if (!panel) return;
  const serverMs = Number(panel.dataset.serverEpoch) * 1000;
  const start = performance.now();
  const wallStart = Date.now();
  function expire() {
    const elapsed = Math.max(performance.now() - start, Date.now() - wallStart, 0);
    const now = (serverMs + elapsed) / 1000;
    panel.querySelectorAll('[data-location-card]').forEach(card => {
      if (Number(card.dataset.expires) <= now) { card.remove(); return; }
      const captured = Number(card.dataset.captured);
      if (captured && now - captured > 30) card.querySelector('[data-freshness]').textContent = 'Stale';
    });
    if (!panel.querySelector('[data-location-card]') && !panel.querySelector('[data-expired-message]')) {
      const message = document.createElement('p');
      message.dataset.expiredMessage = 'true';
      message.textContent = 'No unexpired positions on this page. Refresh to check current sharing.';
      panel.appendChild(message);
    }
  }
  expire(); setInterval(expire, 1000);
  document.addEventListener('visibilitychange', expire);
  window.addEventListener('pageshow', expire);
})();
