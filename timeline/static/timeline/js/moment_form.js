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

    // À la création : prévient (sans bloquer) si un moment existe déjà à une semaine près
    const form = document.querySelector("[data-nearby-url]");
    const banner = document.querySelector("[data-nearby]");
    if (form && banner && start && end) {
        let timer, request = 0;
        const check = async () => {
            if (!start.value) { banner.hidden = true; return; }
            const mine = ++request;
            try {
                const query = new URLSearchParams({ du: start.value, au: end.value || start.value });
                const response = await fetch(`${form.dataset.nearbyUrl}?${query}`);
                if (!response.ok || mine !== request) return;
                const { moments } = await response.json();
                banner.replaceChildren();
                if (!moments.length) { banner.hidden = true; return; }
                const intro = document.createElement("strong");
                intro.textContent = moments.length > 1 ? "Des moments proches existent déjà, c'est peut-être un doublon :" : "Un moment proche existe déjà, c'est peut-être un doublon :";
                const list = document.createElement("ul");
                moments.forEach(moment => {
                    const item = document.createElement("li");
                    const link = document.createElement("a");
                    link.href = moment.url;
                    link.target = "_blank";
                    link.rel = "noopener";
                    link.textContent = moment.nom;
                    item.append(link, ` (${moment.periode})`);
                    list.append(item);
                });
                banner.append(intro, list);
                banner.hidden = false;
            } catch (error) {
                banner.hidden = true;
            }
        };
        const schedule = () => { clearTimeout(timer); timer = setTimeout(check, 300); };
        start.addEventListener("change", schedule);
        end.addEventListener("change", schedule);
        check();
    }
})();

/* Un seul envoi à la fois : les clics supplémentaires sur « Créer / Enregistrer » ne doivent pas créer de doublon */
(() => {
    const form = document.querySelector("form[data-warn-leave]");
    if (!form) return;
    const button = form.querySelector("button[type=submit]");
    let sending = false;

    form.addEventListener("submit", event => {
        if (sending) {
            event.preventDefault();
            return;
        }
        sending = true;
        if (button) button.disabled = true;
    });

    // Retour arrière depuis la page suivante : le formulaire doit être de nouveau utilisable
    window.addEventListener("pageshow", () => {
        sending = false;
        if (button) button.disabled = false;
    });
})();
