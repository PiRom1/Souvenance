/* Visionneuse : un lien [data-lightbox="lot"] ouvre la photo en grand, sans cadre, et on défile dans les photos
   du même lot, avec légende, personnes taguées, auteur de la note, bandeau de miniatures et choix de la vignette */
(() => {
    let overlay, image, counter, caption, strip, action;
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
                <img class="sv-lightbox__img" alt="">
                <figcaption class="sv-lightbox__caption"></figcaption>
                <div class="sv-lightbox__action"></div>
            </figure>
            <button class="sv-lightbox__btn sv-lightbox__btn--next" type="button" aria-label="Photo suivante">›</button>
            <p class="sv-lightbox__counter" aria-live="polite"></p>
            <div class="sv-lightbox__strip"></div>`;
        document.body.append(overlay);
        image = overlay.querySelector(".sv-lightbox__img");
        caption = overlay.querySelector(".sv-lightbox__caption");
        action = overlay.querySelector(".sv-lightbox__action");
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
        action.replaceChildren();
        if (!figure) return;

        const legend = figure.querySelector(".sv-photo__text");
        if (legend) caption.append(text("p", "sv-lightbox__legend", legend.textContent));

        const faces = [...figure.querySelectorAll(".sv-photo__faces img")];
        if (faces.length) {
            const tags = document.createElement("ul");
            tags.className = "sv-lightbox__tags";
            faces.forEach(face => {
                const tag = document.createElement("li");
                tag.className = "sv-lightbox__tag";
                const avatar = document.createElement("img");
                avatar.className = "sv-face";
                avatar.src = face.src;
                avatar.alt = "";
                tag.append(avatar, text("span", "", face.alt));
                tags.append(tag);
            });
            caption.append(tags);
        }

        if (figure.dataset.credit) caption.append(text("p", "sv-lightbox__credit", figure.dataset.credit));

        const thumb = figure.querySelector(".sv-photo__thumb, .sv-photo__badge");
        if (thumb) action.append(thumb.cloneNode(true));
        else if (figure.dataset.thumb === "0") action.append(text("p", "sv-lightbox__hint", "Seuls les participants du moment peuvent choisir la vignette."));
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
