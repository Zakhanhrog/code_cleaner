document.addEventListener('DOMContentLoaded', () => {
    const codeInput = document.getElementById('codeInput');
    const languageSelect = document.getElementById('languageSelect');
    const processButton = document.getElementById('processButton');
    const codeOutput = document.getElementById('codeOutput');
    const codeOutputDisplay = document.getElementById('codeOutputDisplay');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorDisplay = document.getElementById('errorDisplay');
    const exportButton = document.getElementById('exportButton');
    const prismLanguageMap = {
        python: 'python',
        javascript: 'javascript',
        java: 'java',
        csharp: 'csharp',
        c_cpp: 'cpp',
        html: 'markup',
        css: 'css',
        php: 'php',
        ruby: 'ruby',
        go: 'go',
        rust: 'rust',
        sql: 'sql',
        shell: 'bash',
        swift: 'swift',
        kotlin: 'kotlin',
        jsp: 'markup'
    };
    processButton.addEventListener('click', async () => {
        const rawCode = codeInput.value;
        const selectedLanguageKey = languageSelect.value;
        if (!rawCode.trim()) {
            showError('Vui lòng nhập code để xử lý.');
            exportButton.style.display = 'none';
            return;
        }
        hideError();
        codeOutput.textContent = 'Đang xử lý và tô màu...';
        codeOutput.className = 'language-plaintext';
        exportButton.style.display = 'none';
        if (Prism && Prism.highlightElement) {
            Prism.highlightElement(codeOutput);
        }
        loadingIndicator.style.display = 'block';
        try {
            const response = await fetch('/process_code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ code: rawCode, language: selectedLanguageKey }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Lỗi máy chủ: ${response.status}`);
            }
            const data = await response.json();
            if (data.error) {
                showError(data.error);
                codeOutput.textContent = `Lỗi: ${data.error}`;
                codeOutput.className = 'language-plaintext';
                exportButton.style.display = 'none';
                } else {
                    codeOutput.textContent = data.processed_code;
                    const prismLangClass = prismLanguageMap[selectedLanguageKey] || 'plaintext';
                    codeOutput.className = `language-${prismLangClass}`;
                    if (data.processed_code.trim()) {
                        exportButton.style.display = 'inline-block';
                        } else {
                            exportButton.style.display = 'none';
                        }
                    }
                    if (Prism && Prism.highlightElement) {
                        Prism.highlightElement(codeOutput);
                    }
                    } catch (error) {
                        console.error('Lỗi:', error);
                        showError(`Đã xảy ra lỗi: ${error.message}`);
                        codeOutput.textContent = `Lỗi: ${error.message}`;
                        codeOutput.className = 'language-plaintext';
                        exportButton.style.display = 'none';
                        if (Prism && Prism.highlightElement) {
                            Prism.highlightElement(codeOutput);
                        }
                        } finally {
                            loadingIndicator.style.display = 'none';
                        }
                    });
                    exportButton.addEventListener('click', () => {
                        const textToSave = codeOutput.textContent;
                        if (!textToSave.trim()) {
                            alert("Không có nội dung để xuất file.");
                            return;
                        }
                        const selectedLanguage = languageSelect.options[languageSelect.selectedIndex].text.toLowerCase().replace(/[^a-z0-9]/gi, '_');
                        const defaultFileName = `cleaned_code_${selectedLanguage}.txt`;
                        const blob = new Blob([textToSave], { type: 'text/plain;charset=utf-8' });
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement('a');
                        link.href = url;
                        link.download = defaultFileName;
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);
                        URL.revokeObjectURL(url);
                    });
                    function showError(message) {
                        errorDisplay.textContent = message;
                        errorDisplay.style.display = 'block';
                    }
                    function hideError() {
                        errorDisplay.style.display = 'none';
                        errorDisplay.textContent = '';
                    }
                });