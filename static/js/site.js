// Site-wide setup that needs Bootstrap and AOS. Loaded with `defer`, after
// both libraries, so it runs once the page has been parsed.
(function () {
  if (window.AOS) {
    // Scroll animations on larger screens only: on phones they cost a lot of
    // CPU for little benefit, so content is simply shown.
    AOS.init({ duration: 800, once: true, disable: window.innerWidth < 768 });
  }
  if (window.bootstrap) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
      new bootstrap.Tooltip(el);
    });
  }

  // The OpenWidget chat is a third-party script; start it once the visitor
  // interacts with the page (or opens the chat button), so it doesn't compete
  // with the page's own content.
  function startChat() {
    if (typeof window.__owStart === 'function') window.__owStart();
  }
  window.addEventListener('load', function () {
    ['scroll', 'pointerdown', 'keydown', 'touchstart'].forEach(function (evt) {
      window.addEventListener(evt, startChat, { once: true, passive: true });
    });
  });
})();
