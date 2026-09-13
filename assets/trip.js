(() => {
  const dialog = document.querySelector('.trip-lightbox');
  const photos = Array.from(document.querySelectorAll('.trip-report .trip-photo a'));
  if (!dialog || typeof dialog.showModal !== 'function' || !photos.length) return;

  const image = dialog.querySelector('img');
  const caption = dialog.querySelector('figcaption');
  let current = 0;
  let opener;

  function show(index) {
    current = (index + photos.length) % photos.length;
    image.src = photos[current].href;
    image.alt = photos[current].querySelector('img').alt;
    caption.textContent = `${image.alt} · ${current + 1} / ${photos.length}`;
  }

  photos.forEach((photo, index) => {
    photo.addEventListener('click', (event) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      opener = photo;
      show(index);
      dialog.showModal();
    });
  });

  dialog.querySelector('.trip-lightbox-close').addEventListener('click', () => dialog.close());
  dialog.querySelector('.trip-lightbox-prev').addEventListener('click', () => show(current - 1));
  dialog.querySelector('.trip-lightbox-next').addEventListener('click', () => show(current + 1));
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      show(current + (event.key === 'ArrowLeft' ? -1 : 1));
    }
  });
  dialog.addEventListener('close', () => {
    image.removeAttribute('src');
    opener?.focus({ preventScroll: true });
  });
})();
