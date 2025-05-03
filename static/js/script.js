function fetchVideos(letter) {
    fetch(`/videos/${letter}`)
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('video-container');
            container.innerHTML = '';
            data.forEach(video => {
                const videoElem = document.createElement('div');
                videoElem.className = 'video-item';
                videoElem.innerHTML = `<h3>${video.title}</h3><iframe src="${video.url}" frameborder="10" allowfullscreen></iframe>`;
                container.appendChild(videoElem);
            });
        })
        .catch(error => console.error('Error fetching videos:', error));
}

function uploadSignImage() {
    const name = document.getElementById("sign-name").value;
    const fileInput = document.getElementById("sign-image");
    const responseElement = document.getElementById("upload-response");

    if (!name || !fileInput.files || fileInput.files.length === 0) {
        alert("Please provide a name and select an image.");
        return;
    }

    const file = fileInput.files[0];
    const reader = new FileReader();

    reader.onload = function(event) {
        const imageData = event.target.result.split(",")[1];

        fetch("/upload_sign_image", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: name, image: imageData })
        })
        .then(response => response.json())
        .then(data => {
            responseElement.textContent = data.message || data.error;
        })
        .catch(error => {
            console.error("Error:", error);
            responseElement.textContent = "An error occurred.";
        });
    };

    reader.readAsDataURL(file);
}



const socket = io.connect("http://127.0.0.1:5000");

socket.on("recognized_text", function (data) {
    console.log("Recognized Text:", data.text);
    document.getElementById("recognized-text").innerText = "Recognized Sign: " + data.text;
});

let modelRunning = false; // تم تعطيل الموديل بشكل افتراضي

function toggleModel() {
    modelRunning = !modelRunning;
    const status = modelRunning ? "running" : "stopped";
    document.getElementById("toggleModelButton").innerText = modelRunning ? "Stop Model" : "Start Model";
    document.getElementById("modelStatus").innerText = `Model is ${status}`;

    // إرسال حالة الموديل إلى الخادم
    socket.emit("toggle_model", { running: modelRunning });

    // إيقاف تدفق الفيديو إذا تم إيقاف الموديل
    if (!modelRunning && typeof stopVideoStream === 'function') {
        stopVideoStream();
        if (document.getElementById("recognized-text")) {
            document.getElementById("recognized-text").innerText = "Model is stopped";
        }
    } else if (document.getElementById("recognized-text")) {
        document.getElementById("recognized-text").innerText = "Model is running, ready to start detection";
    }
}

socket.on("model_status", function (data) {
    console.log(`Model status: ${data.status}`);
});

// متغيرات عالمية لتتبع حالة الفيديو
let streamInterval = null;
let currentStream = null;
let lastRecognizedText = "";

// تحديث وظيفة استقبال النص المعترف به
socket.on("recognized_text", function (data) {
    console.log("Recognized Text:", data.text);
    document.getElementById("recognized-text").innerText = "Recognized Sign: " + data.text;

    // حفظ النص المعترف به الأخير إذا كان صالحًا
    if (data.text && data.text !== "Unknown" && data.text !== "") {
        lastRecognizedText = data.text;
    }
});

function startVideoStream(language) {
    // إيقاف أي تدفق سابق
    stopVideoStream();

    const video = document.getElementById("camera");
    // استخدام اللغة المحددة من القائمة المنسدلة إذا لم يتم تمريرها
    const selectedLanguage = language ||
                           (document.getElementById("detection-language") ?
                            document.getElementById("detection-language").value : "en");

    // تأكيد بدء التشغيل مع اللغة المحددة
    console.log(`Starting video stream with language: ${selectedLanguage}`);
    if (document.getElementById("recognized-text")) {
        document.getElementById("recognized-text").innerText =
            `Starting detection in ${selectedLanguage === 'ar' ? 'Arabic' : 'English'} mode...`;
    }

    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            currentStream = stream;
            video.srcObject = stream;

            const canvas = document.createElement("canvas");
            const ctx = canvas.getContext("2d");

            streamInterval = setInterval(() => {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

                canvas.toBlob(blob => {
                    socket.emit("video_frame", {
                        frame: blob,
                        language: selectedLanguage
                    });
                }, "image/jpeg");
            }, 500); // إرسال إطار كل 500 مللي ثانية
        })
        .catch(error => {
            console.error("Error accessing camera:", error);
            alert("Please allow camera permissions.");
        });
}

function stopVideoStream() {
    if (streamInterval) {
        clearInterval(streamInterval);
        streamInterval = null;

        if (currentStream) {
            const tracks = currentStream.getTracks();
            tracks.forEach(track => track.stop());
            currentStream = null;
        }

        if (document.getElementById("recognized-text")) {
            document.getElementById("recognized-text").innerText = "Detection stopped";
        }
        console.log("Video stream stopped");
    }
}

// وظيفة إضافة النص المعترف به إلى الجملة
function addToSentence() {
    if (lastRecognizedText && lastRecognizedText !== "Unknown") {
        const currentSentence = document.getElementById("current-sentence");
        if (currentSentence) {
            const currentText = currentSentence.innerText;

            if (currentText) {
                currentSentence.innerText = currentText + " " + lastRecognizedText;
            } else {
                currentSentence.innerText = lastRecognizedText;
            }

            // تنظيف النص المعترف به الأخير بعد إضافته
            lastRecognizedText = "";
            if (document.getElementById("recognized-text")) {
                document.getElementById("recognized-text").innerText = "Ready for next sign...";
            }
        }
    } else {
        alert("No sign detected to add to sentence");
    }
}

// وظيفة مسح الجملة الحالية
function clearSentence() {
    const currentSentence = document.getElementById("current-sentence");
    if (currentSentence) {
        currentSentence.innerText = "";
        console.log("Sentence cleared");
    }
}

// وظيفة للتبديل بين تبويبات التعرف على الإشارات
function switchDetectionTab(tabId) {
    // إخفاء جميع التبويبات
    document.querySelectorAll('.detection-tab').forEach(tab => {
        tab.classList.add('hidden');
    });

    // إظهار التبويب المحدد
    document.getElementById(tabId).classList.remove('hidden');

    // تحديث أزرار التبويب
    document.getElementById('stream-tab-btn').classList.remove('text-blue-500', 'border-blue-500');
    document.getElementById('stream-tab-btn').classList.add('text-gray-500');
    document.getElementById('capture-tab-btn').classList.remove('text-blue-500', 'border-blue-500');
    document.getElementById('capture-tab-btn').classList.add('text-gray-500');

    if (tabId === 'stream-tab') {
        document.getElementById('stream-tab-btn').classList.remove('text-gray-500');
        document.getElementById('stream-tab-btn').classList.add('text-blue-500', 'border-blue-500');
    } else {
        document.getElementById('capture-tab-btn').classList.remove('text-gray-500');
        document.getElementById('capture-tab-btn').classList.add('text-blue-500', 'border-blue-500');

        // بدء تشغيل الكاميرا لقسم التقاط الصورة
        startCaptureCamera();
    }
}

// وظيفة للتبديل بين طرق التقاط الصورة
function switchCaptureTab(tabId) {
    // إخفاء جميع التبويبات
    document.querySelectorAll('.capture-method-tab').forEach(tab => {
        tab.classList.add('hidden');
    });

    // إظهار التبويب المحدد
    document.getElementById(tabId).classList.remove('hidden');

    // تحديث أزرار التبويب
    document.getElementById('capture-camera-tab-btn').classList.remove('text-blue-500', 'border-blue-500');
    document.getElementById('capture-camera-tab-btn').classList.add('text-gray-500');
    document.getElementById('capture-upload-tab-btn').classList.remove('text-blue-500', 'border-blue-500');
    document.getElementById('capture-upload-tab-btn').classList.add('text-gray-500');

    if (tabId === 'camera-tab') {
        document.getElementById('capture-camera-tab-btn').classList.remove('text-gray-500');
        document.getElementById('capture-camera-tab-btn').classList.add('text-blue-500', 'border-blue-500');

        // بدء تشغيل الكاميرا
        startCaptureCamera();
    } else {
        document.getElementById('capture-upload-tab-btn').classList.remove('text-gray-500');
        document.getElementById('capture-upload-tab-btn').classList.add('text-blue-500', 'border-blue-500');

        // إيقاف الكاميرا إذا كانت تعمل
        stopCaptureCamera();
    }
}

// وظيفة بدء تشغيل الكاميرا لقسم التقاط الصورة
function startCaptureCamera() {
    const video = document.getElementById("capture-camera");

    // إيقاف أي تدفق سابق
    stopCaptureCamera();

    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(error => {
            console.error("Error accessing camera for capture:", error);
            alert("Please allow camera permissions for image capture.");
        });
}

// وظيفة إيقاف الكاميرا
function stopCaptureCamera() {
    const video = document.getElementById("capture-camera");

    if (video.srcObject) {
        const tracks = video.srcObject.getTracks();
        tracks.forEach(track => track.stop());
        video.srcObject = null;
    }
}

// وظيفة التقاط الصورة وتحليلها
function captureImage() {
    const video = document.getElementById("capture-camera");
    const language = document.getElementById("capture-language").value;
    const responseElement = document.getElementById("capture-response");
    const resultContainer = document.getElementById("capture-result");
    const resultTitle = document.getElementById("capture-result-title");
    const videoContainer = document.getElementById("capture-video-container");
    const videoElement = document.getElementById("capture-video");

    // التحقق من أن الكاميرا تعمل
    if (!video.srcObject) {
        alert("Camera is not active. Please allow camera access.");
        return;
    }

    // إظهار حالة التحميل
    responseElement.textContent = "Processing image...";
    resultContainer.classList.remove("hidden");
    resultTitle.textContent = "Processing...";
    videoContainer.classList.add("hidden");

    // إنشاء canvas لالتقاط الصورة
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // تحويل الصورة إلى Base64
    const imageData = canvas.toDataURL("image/jpeg").split(",")[1];

    // إرسال الصورة للتحليل
    fetch("/detect_sign", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: imageData, language: language })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            resultTitle.textContent = "Analysis Failed";
            responseElement.textContent = `Error: ${data.error}`;
            videoContainer.classList.add("hidden");
        } else {
            resultTitle.textContent = "Analysis Successful";
            responseElement.textContent = `Detected Sign: ${data.gesture}`;

            // إذا كان هناك فيديو، عرضه
            if (data.video) {
                videoElement.src = data.video;
                videoContainer.classList.remove("hidden");
            } else {
                videoContainer.classList.add("hidden");
            }

            // إذا كان هناك ثقة، عرضها
            if (data.confidence) {
                responseElement.textContent += ` (Confidence: ${Math.round(data.confidence * 100)}%)`;
            }
        }
    })
    .catch(error => {
        console.error("Error:", error);
        resultTitle.textContent = "Error";
        responseElement.textContent = "An error occurred while processing the image.";
        videoContainer.classList.add("hidden");
    });
}

// وظيفة لعرض معاينة الصورة المحملة
document.addEventListener('DOMContentLoaded', function() {
    const uploadSignImage = document.getElementById('upload-sign-image');
    if (uploadSignImage) {
        uploadSignImage.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const imageURL = URL.createObjectURL(file);
                const imagePreview = document.getElementById('upload-sign-image-preview');
                imagePreview.src = imageURL;
                document.getElementById('upload-sign-preview').classList.remove('hidden');
            }
        });
    }
});

// وظيفة تحليل الصورة المحملة
function analyzeUploadedImage() {
    const fileInput = document.getElementById("upload-sign-image");
    const language = document.getElementById("capture-language").value;
    const responseElement = document.getElementById("capture-response");
    const resultContainer = document.getElementById("capture-result");
    const resultTitle = document.getElementById("capture-result-title");
    const videoContainer = document.getElementById("capture-video-container");
    const videoElement = document.getElementById("capture-video");

    // التحقق من وجود ملف
    if (!fileInput.files || fileInput.files.length === 0) {
        alert("Please select an image.");
        return;
    }

    // إظهار حالة التحميل
    responseElement.textContent = "Processing image...";
    resultContainer.classList.remove("hidden");
    resultTitle.textContent = "Processing...";
    videoContainer.classList.add("hidden");

    const file = fileInput.files[0];
    const reader = new FileReader();

    reader.onload = function(event) {
        const imageData = event.target.result.split(",")[1];

        // إرسال الصورة للتحليل
        fetch("/detect_sign", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: imageData, language: language })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                resultTitle.textContent = "Analysis Failed";
                responseElement.textContent = `Error: ${data.error}`;
                videoContainer.classList.add("hidden");
            } else {
                resultTitle.textContent = "Analysis Successful";
                responseElement.textContent = `Detected Sign: ${data.gesture}`;

                // إذا كان هناك فيديو، عرضه
                if (data.video) {
                    videoElement.src = data.video;
                    videoContainer.classList.remove("hidden");
                } else {
                    videoContainer.classList.add("hidden");
                }

                // إذا كان هناك ثقة، عرضها
                if (data.confidence) {
                    responseElement.textContent += ` (Confidence: ${Math.round(data.confidence * 100)}%)`;
                }
            }
        })
        .catch(error => {
            console.error("Error:", error);
            resultTitle.textContent = "Error";
            responseElement.textContent = "An error occurred while processing the image.";
            videoContainer.classList.add("hidden");
        });
    };

    reader.readAsDataURL(file);
}
