/* Date et heure de prise de vue d'un fichier JPEG, lues dans son EXIF (DateTimeOriginal, sinon DateTime) :
   { day: "AAAA-MM-JJ", time: "HH:MM" } ou null */
async function readExifDate(file) {
    try {
        const view = new DataView(await file.slice(0, 262144).arrayBuffer());
        if (view.getUint16(0) !== 0xFFD8) return null;
        let offset = 2;
        while (offset + 4 < view.byteLength) {
            const marker = view.getUint16(offset);
            const size = view.getUint16(offset + 2);
            if (marker === 0xFFE1 && view.getUint32(offset + 4) === 0x45786966) {      // "Exif"
                const tiff = offset + 10;
                const little = view.getUint16(tiff) === 0x4949;
                const u16 = at => view.getUint16(at, little);
                const u32 = at => view.getUint32(at, little);
                const text = (at, length) => String.fromCharCode(...new Uint8Array(view.buffer, at, length));
                const find = (ifd, wanted) => {
                    const count = u16(tiff + ifd);
                    for (let i = 0; i < count; i++) {
                        const entry = tiff + ifd + 2 + i * 12;
                        if (u16(entry) === wanted) return { type: u16(entry + 2), count: u32(entry + 4), value: entry + 8 };
                    }
                    return null;
                };
                const readDate = entry => {
                    if (!entry || entry.count < 10) return null;
                    const at = entry.count > 4 ? tiff + u32(entry.value) : entry.value;
                    const match = /^(\d{4}):(\d{2}):(\d{2})(?: (\d{2}):(\d{2}))?/.exec(text(at, Math.min(entry.count, 19)));
                    return match && match[1] !== "0000" ? { day: `${match[1]}-${match[2]}-${match[3]}`, time: match[4] ? `${match[4]}:${match[5]}` : null } : null;
                };
                const first = u32(tiff + 4);
                const exif = find(first, 0x8769);
                return readDate(exif && find(u32(exif.value), 0x9003)) || readDate(find(first, 0x0132));
            }
            if ((marker & 0xFF00) !== 0xFF00 || size < 2) return null;
            offset += 2 + size;
        }
    } catch (error) {
        return null;
    }
    return null;
}

/* Formulaire de note : les photos jointes s'éditent une à une dans l'éditeur de droite (légende, personnes, date) */
(() => {
    const input = document.querySelector("#id_images");
    const editor = document.querySelector("[data-editor]");
    if (!input || !editor) return;

    const slidesBox = editor.querySelector("[data-slides]");
    const stage = editor.querySelector("[data-stage]");
    const strip = editor.querySelector("[data-strip]");
    const empty = editor.querySelector("[data-empty]");
    const counter = editor.querySelector("[data-counter]");
    const template = document.querySelector("#new-image-template");
    const hint = document.querySelector("[data-clip-hint]");
    const drop = document.querySelector("[data-drop]");
    const defaultDate = editor.dataset.defaultDate;     // jour du moment : date proposée pour les nouvelles photos

    const slides = [];       // { element, file } : les photos déjà sur la note, puis les nouvelles
    let current = 0;

    // Le champ fichier ne contient que ce qu'on lui donne : on y remet les nouvelles photos retenues
    function syncInput() {
        const transfer = new DataTransfer();
        slides.filter(slide => slide.file).forEach(slide => transfer.items.add(slide.file));
        input.files = transfer.files;
    }

    // Les champs des nouvelles photos sont nommés new-<position>-... : on renumérote après chaque ajout/retrait
    function renumber() {
        slides.filter(slide => slide.file).forEach((slide, i) => {
            slide.element.querySelectorAll("[name], [id], [for]").forEach(node => {
                ["name", "id", "for"].forEach(attr => {
                    if (node.hasAttribute(attr)) node.setAttribute(attr, node.getAttribute(attr).replace(/new-\d+-/, `new-${i}-`));
                });
            });
        });
    }

    function buildStrip() {
        strip.replaceChildren();
        slides.forEach((slide, i) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "sv-photoeditor__thumb";
            button.setAttribute("aria-label", `Photo ${i + 1}`);
            button.dataset.index = i;
            const picture = document.createElement("img");
            picture.alt = "";
            picture.src = slide.element.querySelector("img").src;
            button.append(picture);
            strip.append(button);
        });
        const add = document.createElement("label");
        add.className = "sv-photoeditor__thumb sv-photoeditor__thumb--add";
        add.htmlFor = input.id;
        add.title = "Joindre d'autres photos";
        add.textContent = "+";
        strip.append(add);
    }

    function show(index) {
        current = Math.max(0, Math.min(slides.length - 1, index));
        slides.forEach((slide, i) => { slide.element.hidden = i !== current; });
        strip.querySelectorAll("[data-index]").forEach(button => {
            const active = Number(button.dataset.index) === current;
            button.classList.toggle("is-current", active);
            if (active) button.scrollIntoView({ block: "nearest", inline: "center" });
            button.classList.toggle("is-removed", slides[Number(button.dataset.index)].element.classList.contains("is-removed"));
        });
        counter.textContent = slides.length ? `${current + 1} sur ${slides.length}` : "";
        editor.querySelector("[data-prev]").hidden = slides.length < 2;
        editor.querySelector("[data-next]").hidden = slides.length < 2;
    }

    function refresh(target = current) {
        const any = slides.length > 0;
        stage.hidden = !any;
        strip.hidden = !any;
        empty.hidden = any;
        const fresh = slides.filter(slide => slide.file).length;
        hint.textContent = fresh ? `${fresh} photo${fresh > 1 ? "s" : ""} jointe${fresh > 1 ? "s" : ""} · en ajouter d'autres` : "Clique ou glisse-les ici";
        buildStrip();
        show(target);
    }

    function addFile(file) {
        const element = document.createElement("div");
        element.className = "sv-photoeditor__slide";
        element.dataset.slide = "";
        element.hidden = true;
        element.innerHTML = template.innerHTML.replaceAll("__i__", slides.filter(slide => slide.file).length);
        element.querySelector("img").src = URL.createObjectURL(file);
        element.querySelector('input[name$="-nom"]').value = file.name;
        const taken = element.querySelector('input[name$="-jour"]');
        const hour = element.querySelector('input[name$="-heure"]');
        const hourLabel = element.querySelector("[data-time]");
        if (taken && defaultDate && !taken.value) taken.value = defaultDate;
        // Si la photo porte sa vraie date de prise de vue, elle remplace le jour proposé (sauf si on l'a déjà changé)
        // et son heure s'affiche à côté
        readExifDate(file).then(found => {
            if (!found || !taken || (taken.value && taken.value !== defaultDate)) return;
            taken.value = found.day;
            if (found.time) {
                hour.value = found.time;
                hourLabel.querySelector("[data-time-value]").textContent = found.time;
                hourLabel.hidden = false;
            }
        });
        element.querySelector("[data-remove]").addEventListener("click", () => {
            const index = slides.findIndex(slide => slide.element === element);
            URL.revokeObjectURL(element.querySelector("img").src);
            slides.splice(index, 1);
            element.remove();
            syncInput();
            renumber();
            refresh(Math.min(index, slides.length - 1));
        });
        slidesBox.append(element);
        slides.push({ element, file });
    }

    function addFiles(files) {
        const already = file => slides.some(slide => slide.file && slide.file.name === file.name
            && slide.file.size === file.size && slide.file.lastModified === file.lastModified);
        const fresh = [...files].filter(file => file.type.startsWith("image/") && !already(file));
        if (!fresh.length) return;
        const first = slides.length;
        fresh.forEach(addFile);
        syncInput();
        refresh(first);
    }

    // Photos déjà sur la note (modification)
    slidesBox.querySelectorAll("[data-slide]").forEach(element => {
        slides.push({ element, file: null });
        const toggle = element.querySelector('input[type="checkbox"][name$="-DELETE"]');
        if (toggle) toggle.addEventListener("change", () => { element.classList.toggle("is-removed", toggle.checked); show(current); });
        if (toggle && toggle.checked) element.classList.add("is-removed");
    });

    // Les personnes sur la photo : tout le monde d'un coup, ou personne
    editor.addEventListener("click", event => {
        const all = event.target.closest("[data-tags-all]");
        const none = event.target.closest("[data-tags-none]");
        if (!all && !none) return;
        event.target.closest(".sv-photoeditor__slide").querySelectorAll('input[type="checkbox"][name$="-tags"]')
            .forEach(box => { box.checked = Boolean(all); });
    });

    input.addEventListener("change", () => addFiles(input.files));
    strip.addEventListener("click", event => {
        const button = event.target.closest("[data-index]");
        if (button) show(Number(button.dataset.index));
    });
    editor.querySelector("[data-prev]").addEventListener("click", () => show((current - 1 + slides.length) % slides.length));
    editor.querySelector("[data-next]").addEventListener("click", () => show((current + 1) % slides.length));

    // Glisser-déposer sur le bouton ou sur l'éditeur
    [drop, editor].forEach(zone => {
        ["dragenter", "dragover"].forEach(name => zone.addEventListener(name, event => {
            if (!event.dataTransfer || ![...event.dataTransfer.types].includes("Files")) return;
            event.preventDefault();
            zone.classList.add("is-dragover");
        }));
        ["dragleave", "drop"].forEach(name => zone.addEventListener(name, event => {
            if (name === "dragleave" && zone.contains(event.relatedTarget)) return;
            zone.classList.remove("is-dragover");
        }));
        zone.addEventListener("drop", event => {
            if (!event.dataTransfer || !event.dataTransfer.files.length) return;
            event.preventDefault();
            addFiles(event.dataTransfer.files);
        });
    });

    refresh(0);
})();
