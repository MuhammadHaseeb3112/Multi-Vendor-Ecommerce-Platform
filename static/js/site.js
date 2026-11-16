// Site-wide setup that needs Bootstrap and AOS. Loaded with `defer`, after
// both libraries, so it runs once the page has been parsed.
(function () {
  if (window.AOS) {
    AOS.init({ duration: 800, once: true });
  }
  if (window.bootstrap) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
      new bootstrap.Tooltip(el);
    });
  }

  // The OpenWidget chat is a third-party script; start it after the page has
  // loaded and the visitor interacts (or after a few seconds) so it doesn't
  // compete with the page's own content.
  function startChat() {
    if (typeof window.__owStart === 'function') window.__owStart();
  }
  window.addEventListener('load', function () {
    ['scroll', 'pointerdown', 'keydown', 'touchstart'].forEach(function (evt) {
      window.addEventListener(evt, startChat, { once: true, passive: true });
    });
    setTimeout(startChat, 6000);
  });
})();
