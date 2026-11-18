/* Photothèque : filtre par personne taguée */
(() => {
    const checkboxes = [...document.querySelectorAll("[data-gallery-person]")];
    const photos = [...document.querySelectorAll("[data-gallery] [data-photo]")];
    if (!checkboxes.length) return;

    function apply() {
        const people = checkboxes.filter(box => box.checked).map(box => box.value);
        photos.forEach(photo => {
            const tags = photo.dataset.tags.trim().split(/\s+/);
            photo.hidden = people.length > 0 && !people.some(person => tags.includes(person));
        });
    }

    checkboxes.forEach(box => box.addEventListener("change", apply));
})();
