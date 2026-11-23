/* Prévient avant de quitter un formulaire [data-warn-leave] modifié mais pas enregistré.
   Les liens [data-leave-link] (Annuler…) demandent confirmation ; fermer l'onglet ou revenir en arrière
   déclenche l'alerte du navigateur (qui impose son propre texte). */
(() => {
    const form = document.querySelector("[data-warn-leave]");
    if (!form) return;

    let dirty = false;
    const markDirty = () => { dirty = true; };

    form.addEventListener("input", markDirty);
    form.addEventListener("change", markDirty);
    // Les boutons qui modifient des cases ou retirent une photo sans déclencher d'évènement
    form.addEventListener("click", event => {
        if (event.target.closest("[data-people-all], [data-people-none], [data-tags-all], [data-tags-none], [data-remove]")) markDirty();
    });
    form.addEventListener("submit", () => { dirty = false; });

    window.addEventListener("beforeunload", event => {
        if (!dirty) return;
        event.preventDefault();
        event.returnValue = "";
    });

    document.querySelectorAll("[data-leave-link]").forEach(link => {
        link.addEventListener("click", event => {
            if (!dirty) return;
            if (confirm("Tu n'as rien enregistré, tu vas tout perdre si tu quittes cette page. Quitter quand même ?")) {
                dirty = false;
            } else {
                event.preventDefault();
            }
        });
    });
})();
