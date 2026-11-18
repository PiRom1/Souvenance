/* Formulaire de moment : sélection rapide des participants et cohérence des dates */
(() => {
    const people = document.querySelector("[data-people]");
    if (!people) return;
    const boxes = [...people.querySelectorAll("input[type=checkbox]")];
    const count = people.querySelector("[data-people-count]");

    function refresh() {
        const checked = boxes.filter(box => box.checked).length;
        count.textContent = `${checked} sur ${boxes.length}`;
    }

    function setAll(value) {
        boxes.forEach(box => { box.checked = value; });
        refresh();
    }

    people.querySelector("[data-people-all]").addEventListener("click", () => setAll(true));
    people.querySelector("[data-people-none]").addEventListener("click", () => setAll(false));
    boxes.forEach(box => box.addEventListener("change", refresh));
    refresh();

    // Le dernier jour suit le premier tant qu'on ne l'a pas choisi à part, et ne peut pas le précéder
    const start = document.querySelector("#id_date_debut");
    const end = document.querySelector("#id_date_fin");
    if (start && end) {
        let previous = start.value;
        const sync = () => {
            end.min = start.value || "";
            if (start.value && (!end.value || end.value < start.value || end.value === previous)) end.value = start.value;
            previous = start.value;
        };
        start.addEventListener("change", sync);
        end.min = start.value || "";
    }
})();
