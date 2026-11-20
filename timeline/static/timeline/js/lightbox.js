/* Visionneuse : un lien [data-lightbox="lot"] ouvre la photo en grand, sans cadre, et on défile dans les photos
   du même lot, avec légende, personnes taguées, auteur de la note, bandeau de miniatures et choix de la vignette */
(() => {
    let overlay, image, counter, caption, strip, action, peopleZone;
    let items = [], index = 0;

    function build() {
        overlay = document.createElement("div");
        overlay.className = "sv-lightbox";
        overlay.hidden = true;
        overlay.setAttribute("role", "dialog");
        overlay.setAttribute("aria-modal", "true");
        overlay.innerHTML = `
            <button class="sv-lightbox__btn sv-lightbox__btn--close" type="button" aria-label="Fermer">×</button>
            <button class="sv-lightbox__btn sv-lightbox__btn--prev" type="button" aria-label="Photo précédente">‹</button>
            <figure class="sv-lightbox__figure">
                <div class="sv-lightbox__action"></div>
                <img class="sv-lightbox__img" alt="">
                <figcaption class="sv-lightbox__caption"></figcaption>
                <div class="sv-lightbox__people-zone"></div>
            </figure>
            <button class="sv-lightbox__btn sv-lightbox__btn--next" type="button" aria-label="Photo suivante">›</button>
            <p class="sv-lightbox__counter" aria-live="polite"></p>
            <div class="sv-lightbox__strip"></div>`;
        document.body.append(overlay);
        image = overlay.querySelector(".sv-lightbox__img");
        caption = overlay.querySelector(".sv-lightbox__caption");
        action = overlay.querySelector(".sv-lightbox__action");
        peopleZone = overlay.querySelector(".sv-lightbox__people-zone");
        action.addEventListener("submit", chooseThumbnail);
        counter = overlay.querySelector(".sv-lightbox__counter");
        strip = overlay.querySelector(".sv-lightbox__strip");
        overlay.querySelector(".sv-lightbox__btn--close").addEventListener("click", close);
        overlay.querySelector(".sv-lightbox__btn--prev").addEventListener("click", () => show(index - 1));
        overlay.querySelector(".sv-lightbox__btn--next").addEventListener("click", () => show(index + 1));
        overlay.addEventListener("click", event => {
            if (event.target === overlay || event.target.classList.contains("sv-lightbox__figure")) close();
        });
        // La molette (ou le pavé tactile) fait défiler les photos du lot, une par geste
        let lastWheel = 0;
        overlay.addEventListener("wheel", event => {
            event.preventDefault();
            const delta = Math.abs(event.deltaY) > Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
            const now = performance.now();
            if (Math.abs(delta) < 4 || now - lastWheel < 380) return;
            lastWheel = now;
            show(index + (delta > 0 ? 1 : -1));
        }, { passive: false });
        strip.addEventListener("click", event => {
            const thumb = event.target.closest("[data-strip-index]");
            if (thumb) show(Number(thumb.dataset.stripIndex));
        });
    }

    function text(tag, className, content) {
        const element = document.createElement(tag);
        element.className = className;
        element.textContent = content;
        return element;
    }

    function fillCaption(figure) {
        caption.replaceChildren();
        if (!figure) return;

        const legend = figure.querySelector(".sv-photo__text");
        if (legend) caption.append(text("p", "sv-lightbox__legend", legend.textContent));

        if (figure.dataset.credit) caption.append(text("p", "sv-lightbox__credit", figure.dataset.credit));
    }

    // Les membres de la bande, pour pouvoir taguer (absents si la page ne les fournit pas)
    function members() {
        try { return JSON.parse(document.getElementById("sv-membres").textContent); } catch { return []; }
    }

    // Met à jour la figure de la page (légende sous la photo, filtre par personne) après un changement de tags
    function applyTags(figure, tags) {
        figure.dataset.tags = tags.map(tag => tag.username).join(" ");
        let figcaption = figure.querySelector(".sv-photo__caption");
        if (!figcaption) {
            figcaption = document.createElement("figcaption");
            figcaption.className = "sv-photo__caption";
            figure.querySelector(".sv-photo__link").after(figcaption);
        }
        figcaption.querySelector(".sv-photo__faces")?.remove();
        if (tags.length) {
            const faces = document.createElement("span");
            faces.className = "sv-photo__faces";
            tags.forEach(tag => {
                const face = document.createElement("img");
                face.className = "sv-face sv-face--tiny";
                face.src = tag.avatar;
                face.alt = face.title = tag.nom;
                faces.append(face);
            });
            figcaption.append(faces);
        }
        if (!figcaption.children.length) figcaption.remove();
    }

    // Les têtes de tous les membres sous la photo, celles des personnes taguées en évidence ; tout le monde peut modifier
    // les tags : un clic sur une tête l'ajoute ou la retire aussitôt
    function tagEditor(figure) {
        const people = members();
        if (!people.length || !figure.dataset.imageId) return null;
        const selected = new Set((figure.dataset.tags || "").split(" ").filter(Boolean));
        const wrapper = document.createElement("div");
        wrapper.className = "sv-lightbox__edit";
        const panel = document.createElement("div");
        panel.className = "sv-lightbox__people";

        const buttons = people.map(person => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "sv-lightbox__person";
            const avatar = document.createElement("img");
            avatar.className = "sv-face";
            avatar.src = person.avatar;
            avatar.alt = "";
            button.append(avatar, text("span", "", person.nom));
            button.addEventListener("click", async () => {
                if (selected.has(person.username)) selected.delete(person.username); else selected.add(person.username);
                refresh();
                const body = new URLSearchParams();
                people.filter(p => selected.has(p.username)).forEach(p => body.append("tags", p.id));
                panel.classList.add("is-saving");
                try {
                    const response = await fetch(`/image/${figure.dataset.imageId}/tags`, {
                        method: "POST",
                        headers: { "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]").value },
                        body,
                    });
                    if (!response.ok) throw new Error(response.status);
                    applyTags(figure, (await response.json()).tags);
                } catch {
                    alert("Les tags n'ont pas pu être enregistrés, réessaie.");
                } finally {
                    panel.classList.remove("is-saving");
                }
            });
            return { person, button };
        });
        function refresh() {
            buttons.forEach(({ person, button }) => {
                button.classList.toggle("is-on", selected.has(person.username));
                button.setAttribute("aria-pressed", selected.has(person.username));
            });
        }
        refresh();
        panel.append(...buttons.map(({ button }) => button));
        wrapper.append(panel);
        return wrapper;
    }

    function fillAction(figure) {
        action.replaceChildren();
        peopleZone.replaceChildren();
        if (!figure) return;

        const editor = tagEditor(figure);
        if (editor) peopleZone.append(editor);

        const thumb = figure.querySelector(".sv-photo__thumb, .sv-photo__badge");
        if (thumb) action.append(thumb.cloneNode(true));
        else if (figure.dataset.thumb === "0") action.append(text("p", "sv-lightbox__hint", "Seuls les participants du moment peuvent choisir la vignette."));
    }

    // « Choisir comme vignette » sans quitter la photo : on envoie le formulaire en arrière-plan puis on met à jour la page
    async function chooseThumbnail(event) {
        event.preventDefault();
        const form = event.target;
        const figure = items[index].closest("figure");
        try {
            const response = await fetch(form.action, { method: "POST", body: new FormData(form), redirect: "manual" });
            if (response.type !== "opaqueredirect" && !response.ok) throw new Error(response.status);
        } catch {
            alert("La vignette n'a pas pu être changée, réessaie.");
            return;
        }
        const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
        const urlPrefix = form.getAttribute("action").replace(/\d+$/, "");
        document.querySelectorAll("figure[data-image-id]").forEach(other => {
            const badge = other.querySelector(".sv-photo__badge");
            if (badge) {
                const again = document.createElement("form");
                again.className = "sv-photo__thumb";
                again.method = "post";
                again.action = urlPrefix + other.dataset.imageId;
                again.innerHTML = `<input type="hidden" name="csrfmiddlewaretoken" value="${csrf}"><button type="submit">Choisir comme vignette</button>`;
                badge.replaceWith(again);
            }
        });
        const badge = text("span", "sv-photo__badge", "Vignette");
        figure.querySelector(".sv-photo__thumb")?.replaceWith(badge);
        const cover = document.querySelector("[data-lightbox=couverture]");
        if (cover) {
            cover.href = items[index].href;
            cover.querySelector("img").src = figure.querySelector("img").src;
        }
        fillAction(figure);
    }

    function buildStrip() {
        strip.replaceChildren();
        strip.hidden = items.length < 2;
        items.forEach((link, position) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "sv-lightbox__thumb";
            button.dataset.stripIndex = position;
            button.setAttribute("aria-label", `Photo ${position + 1}`);
            const picture = document.createElement("img");
            picture.src = link.querySelector("img")?.src || link.href;     // l'aperçu léger, pas l'original
            picture.alt = "";
            picture.loading = "lazy";
            picture.decoding = "async";
            button.append(picture);
            strip.append(button);
        });
    }

    function show(next) {
        index = (next + items.length) % items.length;
        const link = items[index];
        image.src = link.href;
        image.alt = link.querySelector("img")?.alt ?? "";
        fillCaption(link.closest("figure"));
        fillAction(link.closest("figure"));
        counter.textContent = items.length > 1 ? `${index + 1} / ${items.length}` : "";
        overlay.querySelectorAll(".sv-lightbox__btn--prev, .sv-lightbox__btn--next").forEach(button => { button.hidden = items.length < 2; });
        strip.querySelectorAll(".sv-lightbox__thumb").forEach((thumb, position) => {
            thumb.classList.toggle("is-current", position === index);
            if (position === index) thumb.scrollIntoView({ block: "nearest", inline: "center" });
        });
    }

    function open(group, start) {
        if (!overlay) build();
        items = [...document.querySelectorAll("[data-lightbox]")]
            .filter(link => link.dataset.lightbox === group && !link.closest("figure[hidden]"));
        if (!items.length) return;
        buildStrip();
        show(Math.max(0, items.indexOf(start)));
        overlay.hidden = false;
        document.body.style.overflow = "hidden";
        overlay.querySelector(".sv-lightbox__btn--close").focus();
    }

    function close() {
        overlay.hidden = true;
        document.body.style.overflow = "";
    }

    document.addEventListener("click", event => {
        const link = event.target.closest("[data-lightbox]");
        if (link) {
            event.preventDefault();
            open(link.dataset.lightbox, link);
            return;
        }
        const more = event.target.closest("[data-open-group]");
        if (more) open(more.dataset.openGroup, null);
    });

    document.addEventListener("keydown", event => {
        if (!overlay || overlay.hidden) return;
        if (event.key === "Escape") close();
        else if (event.key === "ArrowLeft") show(index - 1);
        else if (event.key === "ArrowRight") show(index + 1);
        else return;
        event.stopImmediatePropagation();
    }, true);
})();
