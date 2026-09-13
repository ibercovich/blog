(() => {
  const container = document.querySelector('#trip-map');
  const links = Array.from(document.querySelectorAll('.trip-route-stop'));
  if (!container || !links.length || !window.L) return;

  function initialize() {
    const L = window.L;
    const reset = document.querySelector('.trip-route-reset');
    const status = document.querySelector('.trip-map-status');
    const points = links.map(link => [Number(link.dataset.lat), Number(link.dataset.lon)]);
    const bounds = L.latLngBounds(points);
    const map = L.map(container, { scrollWheelZoom: false, zoomSnap: 0.25 });
    const styles = {
      drive: { color: '#34584d', weight: 4 },
      bike: { color: '#a36620', weight: 4, dashArray: '5 7' },
      train: { color: '#586d87', weight: 4, dashArray: '10 6' }
    };

    container.querySelector('.trip-map-fallback').hidden = true;
    document.querySelector('.trip-route-views').hidden = false;
    map.fitBounds(bounds, { padding: [32, 32] });

    let loadedTiles = 0;
    L.tileLayer(container.dataset.tileUrl, {
      maxZoom: 19,
      keepBuffer: 1,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
    }).on('tileload', () => {
      loadedTiles += 1;
      status.hidden = true;
    }).on('tileerror', () => {
      if (!loadedTiles) {
        status.textContent = 'The background map could not load. The route and stop details are still available.';
        status.hidden = false;
      }
    }).addTo(map);

    links.forEach((link, index) => {
      if (index) {
        L.polyline([points[index - 1], points[index]], {
          ...styles[link.dataset.arrival],
          interactive: false
        }).addTo(map);
      }

      const popup = document.createElement('div');
      const title = document.createElement('strong');
      const description = document.createElement('p');
      const story = document.createElement('a');
      title.textContent = `${index + 1}. ${link.dataset.name}`;
      description.textContent = link.dataset.description;
      story.textContent = 'Read about this stop →';
      story.href = `#${link.dataset.section}`;
      popup.append(title, description, story);

      const marker = L.marker(points[index], {
        title: `${index + 1}. ${link.dataset.name}`,
        icon: L.divIcon({
          className: 'trip-map-marker',
          html: String(index + 1),
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        })
      }).addTo(map).bindPopup(popup, { maxWidth: 250 });
      marker.getElement().setAttribute('aria-label', `${index + 1}. ${link.dataset.name}`);
      marker.on('popupopen', () => {
        links.forEach(item => item.removeAttribute('aria-current'));
        link.setAttribute('aria-current', 'location');
      });
      marker.on('popupclose', () => link.removeAttribute('aria-current'));

      link.addEventListener('click', event => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        map.setView(points[index], 11, { animate: false });
        marker.openPopup();
        container.scrollIntoView({ block: 'nearest' });
        story.focus({ preventScroll: true });
      });
    });

    reset.addEventListener('click', () => {
      map.closePopup();
      map.fitBounds(bounds, { padding: [32, 32], animate: false });
    });
    document.querySelector('.trip-route-slovenia').addEventListener('click', () => {
      map.closePopup();
      map.fitBounds(L.latLngBounds(points.slice(1, 5)), { padding: [32, 32], animate: false });
    });
  }

  // Load tiles when the map comes into view, rather than on every article visit.
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        observer.disconnect();
        initialize();
      }
    });
    observer.observe(container);
  } else {
    initialize();
  }
})();
