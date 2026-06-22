document.addEventListener('DOMContentLoaded', () => {
    // --- Configuration ---
    // The application is full-stack, so the frontend and backend are hosted together.
    // Relative paths will automatically point to the correct domain.
    const BACKEND_URL = '';

    // --- Elements ---
    const form = document.getElementById('generator-form');
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const btnNext = document.getElementById('btn-next');
    const btnBack = document.getElementById('btn-back');
    const templateInput = document.getElementById('template');
    const excelInput = document.getElementById('excel');
    const errorMsg = document.getElementById('error-message');
    const submitBtn = document.getElementById('submit-btn');
    const loaderStep1 = document.getElementById('loader-step1');
    
    const canvasContainer = document.getElementById('canvas-container');
    const previewImg = document.getElementById('preview-image');
    const elementsList = document.getElementById('elements-list');
    const btnAddElement = document.getElementById('btn-add-element');
    const elementTemplate = document.getElementById('element-template');
    
    const configPayload = document.getElementById('config_payload');
    const previewRowPayload = document.getElementById('preview_row_payload');

    let naturalWidth = 1;
    let naturalHeight = 1;
    let availableColumns = [];
    let previewDataRow = {};
    let elements = [];
    let elementIdCounter = 0;

    // --- Drag Logic State ---
    let isDragging = false;
    let activeBox = null;
    let startMouseX, startMouseY;
    let startBoxX, startBoxY;

    // --- STEP 1 -> STEP 2 (Parse Headers) ---
    btnNext.addEventListener('click', async () => {
        if (!templateInput.files.length || !excelInput.files.length) {
            showError("Please upload both files to continue.");
            return;
        }
        hideError();
        btnNext.disabled = true;
        loaderStep1.style.display = 'block';
        btnNext.querySelector('.btn-text').style.opacity = '0';

        try {
            const formData = new FormData();
            formData.append('excel', excelInput.files[0]);

            const response = await fetch(`${BACKEND_URL}/parse-headers`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Failed to parse data file.');
            }

            const data = await response.json();
            availableColumns = data.headers || [];
            previewDataRow = data.preview_row || {};

            // If we have elements, update their dropdowns
            document.querySelectorAll('.column-select').forEach(select => {
                populateColumnDropdown(select, select.value);
            });

            loadPreviewImage(templateInput.files[0]);
            
            step1.classList.remove('active');
            step2.classList.add('active');

            // Add an initial element if none exist
            if (elements.length === 0 && availableColumns.length > 0) {
                addNewElement();
            }

        } catch (err) {
            showError(err.message);
        } finally {
            btnNext.disabled = false;
            loaderStep1.style.display = 'none';
            btnNext.querySelector('.btn-text').style.opacity = '1';
        }
    });

    btnBack.addEventListener('click', () => {
        step2.classList.remove('active');
        step1.classList.add('active');
    });

    // --- PREVIEW IMAGE & SCALING ---
    function loadPreviewImage(file) {
        const url = URL.createObjectURL(file);
        previewImg.src = url;
        previewImg.onload = () => {
            naturalWidth = previewImg.naturalWidth;
            naturalHeight = previewImg.naturalHeight;
            recalculateAllBoxes();
        };
    }

    // --- DYNAMIC ELEMENTS BUILDER ---
    btnAddElement.addEventListener('click', addNewElement);

    function populateColumnDropdown(select, selectedValue = null) {
        select.innerHTML = '';
        availableColumns.forEach(col => {
            const opt = document.createElement('option');
            opt.value = col;
            opt.textContent = col;
            select.appendChild(opt);
        });
        if (selectedValue && availableColumns.includes(selectedValue)) {
            select.value = selectedValue;
        }
    }

    function addNewElement() {
        elementIdCounter++;
        const id = `el-${elementIdCounter}`;
        
        // Data Model
        const defaultCol = availableColumns[0] || "";
        const elData = {
            id: id,
            column: defaultCol,
            font: "Roboto",
            text_color: "#ffffff",
            max_font_size: 43,
            min_font_size: 30,
            max_text_width: 900,
            text_x: 100, // Initial defaults
            text_y: 390
        };
        elements.push(elData);

        // UI Card
        const clone = elementTemplate.content.cloneNode(true);
        const card = clone.querySelector('.element-card');
        card.dataset.id = id;
        
        card.querySelector('.element-title').textContent = `Text Box ${elementIdCounter}`;
        
        const colSelect = card.querySelector('.column-select');
        populateColumnDropdown(colSelect, defaultCol);
        
        // UI Draggable Box
        const dragBox = document.createElement('div');
        dragBox.className = 'draggable-box';
        dragBox.id = `box-${id}`;
        dragBox.dataset.id = id;
        dragBox.textContent = previewDataRow[defaultCol] || `[${defaultCol}]`;
        dragBox.style.fontFamily = '"Roboto", sans-serif';
        canvasContainer.appendChild(dragBox);

        // Setup Card Event Listeners
        setupCardListeners(card, dragBox, elData);
        setupDragBoxListeners(dragBox, elData);

        elementsList.appendChild(card);
        
        // Initial visual sync
        syncBoxVisuals(dragBox, elData);
        
        // If image is loaded, position it safely
        if (previewImg.src && naturalWidth > 1) {
            elData.text_x = naturalWidth / 4;
            elData.text_y = naturalHeight / 2;
            updateBoxPositionFromData(dragBox, elData);
        }
    }

    function setupCardListeners(card, dragBox, elData) {
        const colSelect = card.querySelector('.column-select');
        const fontSelect = card.querySelector('.font-select');
        const colorInput = card.querySelector('.color-input');
        const maxSizeInput = card.querySelector('.max-font-input');
        const maxWidthInput = card.querySelector('.max-width-input');
        const btnDelete = card.querySelector('.btn-delete');

        colSelect.addEventListener('change', (e) => {
            elData.column = e.target.value;
            dragBox.textContent = previewDataRow[elData.column] || `[${elData.column}]`;
        });

        fontSelect.addEventListener('change', (e) => {
            elData.font = e.target.value;
            const fontMap = {
                'Roboto': '"Roboto", sans-serif',
                'OpenSans': '"Open Sans", sans-serif',
                'Montserrat': '"Montserrat", sans-serif',
                'Oswald': '"Oswald", sans-serif',
                'Raleway': '"Raleway", sans-serif',
                'PlayfairDisplay': '"Playfair Display", serif',
                'Lora': '"Lora", serif',
                'DancingScript': '"Dancing Script", cursive',
                'Pacifico': '"Pacifico", cursive'
            };
            dragBox.style.fontFamily = fontMap[elData.font] || 'sans-serif';
        });
        
        colorInput.addEventListener('input', (e) => {
            elData.text_color = e.target.value;
            dragBox.style.color = elData.text_color;
        });

        maxSizeInput.addEventListener('input', (e) => {
            elData.max_font_size = parseInt(e.target.value) || 43;
            syncBoxVisuals(dragBox, elData);
        });

        maxWidthInput.addEventListener('input', (e) => {
            elData.max_text_width = parseInt(e.target.value) || 900;
            syncBoxVisuals(dragBox, elData);
        });

        btnDelete.addEventListener('click', () => {
            elements = elements.filter(e => e.id !== elData.id);
            card.remove();
            dragBox.remove();
        });

        // Hover effect to find box easily
        card.addEventListener('mouseenter', () => dragBox.classList.add('active-box'));
        card.addEventListener('mouseleave', () => dragBox.classList.remove('active-box'));
    }

    function syncBoxVisuals(dragBox, elData) {
        if (!previewImg.src || naturalWidth === 1) return;
        const imgRect = previewImg.getBoundingClientRect();
        const scaleX = imgRect.width / naturalWidth;
        const scaleY = imgRect.height / naturalHeight;

        // Give the box more visual padding and make it taller so it's easier to interact with
        const widthPx = Math.max(60, elData.max_text_width * scaleX);
        const heightPx = Math.max(30, (elData.max_font_size * scaleY) * 1.4);

        dragBox.style.width = `${widthPx}px`;
        dragBox.style.height = `${heightPx}px`;
        dragBox.style.fontSize = `${Math.max(14, heightPx * 0.7)}px`;
        dragBox.style.color = elData.text_color;
    }

    // --- DRAG LOGIC ---
    function setupDragBoxListeners(dragBox, elData) {
        const startDrag = (e) => {
            isDragging = true;
            activeBox = dragBox;
            
            const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
            const clientY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
            
            startMouseX = clientX;
            startMouseY = clientY;
            
            const boxRect = dragBox.getBoundingClientRect();
            const containerRect = canvasContainer.getBoundingClientRect();
            
            startBoxX = boxRect.left - containerRect.left + dragBox.offsetWidth / 2;
            startBoxY = boxRect.top - containerRect.top + dragBox.offsetHeight / 2;
            
            document.querySelectorAll('.element-card').forEach(c => c.classList.remove('active-box'));
            const card = document.querySelector(`.element-card[data-id="${elData.id}"]`);
            if(card) card.classList.add('active-box');

            e.preventDefault(); // Prevents screen scrolling while dragging box
        };
        
        dragBox.addEventListener('mousedown', startDrag);
        dragBox.addEventListener('touchstart', startDrag, {passive: false});
    }

    const moveDrag = (e) => {
        if (!isDragging || !activeBox) return;
        
        const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
        const clientY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;

        const deltaX = clientX - startMouseX;
        const deltaY = clientY - startMouseY;

        let newX = startBoxX + deltaX;
        let newY = startBoxY + deltaY;

        const cRect = canvasContainer.getBoundingClientRect();
        newX = Math.max(0, Math.min(newX, cRect.width));
        newY = Math.max(0, Math.min(newY, cRect.height));

        activeBox.style.left = `${newX}px`;
        activeBox.style.top = `${newY}px`;

        const id = activeBox.dataset.id;
        const elData = elements.find(e => e.id === id);
        if (elData) updateDataFromBox(activeBox, elData);
        
        if (e.type.includes('touch')) e.preventDefault();
    };

    window.addEventListener('mousemove', moveDrag);
    window.addEventListener('touchmove', moveDrag, {passive: false});

    const endDrag = () => {
        if (isDragging) {
            isDragging = false;
            activeBox = null;
        }
    };
    
    window.addEventListener('mouseup', endDrag);
    window.addEventListener('touchend', endDrag);

    function updateDataFromBox(dragBox, elData) {
        if (!previewImg.src || naturalWidth === 1) return;
        
        const imgRect = previewImg.getBoundingClientRect();
        const boxRect = dragBox.getBoundingClientRect();
        
        const visualX = boxRect.left - imgRect.left;
        const visualY = boxRect.top - imgRect.top + boxRect.height / 2; 
        
        const scaleX = naturalWidth / imgRect.width;
        const scaleY = naturalHeight / imgRect.height;
        
        elData.text_x = Math.round(visualX * scaleX);
        elData.text_y = Math.round(visualY * scaleY);
    }

    function updateBoxPositionFromData(dragBox, elData) {
        if (!previewImg.src || naturalWidth === 1) return;
        
        const imgRect = previewImg.getBoundingClientRect();
        const cRect = canvasContainer.getBoundingClientRect();
        
        const scaleX = imgRect.width / naturalWidth;
        const scaleY = imgRect.height / naturalHeight;
        
        const visualX = elData.text_x * scaleX;
        const visualY = elData.text_y * scaleY;
        
        const leftOffset = imgRect.left - cRect.left;
        const topOffset = imgRect.top - cRect.top;
        
        dragBox.style.left = `${visualX + leftOffset + dragBox.offsetWidth / 2}px`;
        dragBox.style.top = `${visualY + topOffset}px`;
    }

    function recalculateAllBoxes() {
        elements.forEach(el => {
            const box = document.getElementById(`box-${el.id}`);
            if (box) {
                syncBoxVisuals(box, el);
                updateBoxPositionFromData(box, el);
            }
        });
    }

    window.addEventListener('resize', () => {
        if (step2.classList.contains('active')) recalculateAllBoxes();
    });

    // --- FORM SUBMIT & PREVIEW LOGIC ---
    function preparePayload() {
        configPayload.value = JSON.stringify({ elements: elements });
        previewRowPayload.value = JSON.stringify(previewDataRow);
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;
        hideError();
        preparePayload();

        try {
            const formData = new FormData(form);
            const response = await fetch(`${BACKEND_URL}/generate`, { method: 'POST', body: formData });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Generation failed.');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'certificates.zip';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (err) {
            showError(err.message);
        } finally {
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
        }
    });

    // --- LIVE PREVIEW MODAL ---
    const btnPreview = document.getElementById('btn-preview');
    const previewModal = document.getElementById('preview-modal');
    const closeModal = document.querySelector('.close-modal');
    const modalImage = document.getElementById('modal-image');
    const modalLoader = document.getElementById('modal-loader');

    btnPreview.addEventListener('click', async () => {
        preparePayload();
        previewModal.style.display = 'block';
        modalImage.style.display = 'none';
        modalLoader.style.display = 'block';
        
        try {
            const formData = new FormData(form);
            const response = await fetch(`${BACKEND_URL}/preview`, { method: 'POST', body: formData });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Preview failed.');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            modalImage.src = url;
            modalImage.onload = () => {
                modalLoader.style.display = 'none';
                modalImage.style.display = 'block';
            };
        } catch (err) {
            showError(err.message);
            previewModal.style.display = 'none';
        }
    });

    closeModal.addEventListener('click', () => previewModal.style.display = 'none');
    window.addEventListener('click', (e) => { if (e.target == previewModal) previewModal.style.display = 'none'; });

    // --- FILE DROPS ---
    const setupFileDrop = (dropZoneId, inputId, textId) => {
        const dropZone = document.getElementById(dropZoneId);
        const input = document.getElementById(inputId);
        const text = document.getElementById(textId);
        const dummy = dropZone.querySelector('.file-dummy');
        const preventDefaults = (e) => { e.preventDefault(); e.stopPropagation(); };

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => dropZone.addEventListener(evt, preventDefaults));
        ['dragenter', 'dragover'].forEach(evt => dropZone.addEventListener(evt, () => dummy.classList.add('active')));
        ['dragleave', 'drop'].forEach(evt => dropZone.addEventListener(evt, () => dummy.classList.remove('active')));

        dropZone.addEventListener('drop', (e) => { input.files = e.dataTransfer.files; updateText(); });
        input.addEventListener('change', updateText);

        function updateText() {
            if (input.files.length > 0) {
                text.textContent = input.files[0].name;
                dummy.style.borderColor = 'var(--primary)';
                dummy.style.background = 'rgba(99, 102, 241, 0.1)';
            } else {
                text.textContent = `Click or Drop ${inputId === 'template' ? 'Template' : 'File'}`;
                dummy.style.borderColor = '';
                dummy.style.background = '';
            }
        }
    };

    setupFileDrop('drop-template', 'template', 'template-text');
    setupFileDrop('drop-excel', 'excel', 'excel-text');

    function showError(msg) { errorMsg.textContent = msg; errorMsg.style.display = 'block'; }
    function hideError() { errorMsg.style.display = 'none'; }
});
