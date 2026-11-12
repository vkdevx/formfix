# FormFix Deployment Guide (डिप्लॉयमेंट गाइड) 🚀🌐

FormFix को **Production** में लाइव करने के लिए सबसे आसान और 100% फ्री तरीके नीचे दिए गए हैं।

हमने पूरे प्रोजेक्ट को इस तरह कॉन्फ़िगर कर दिया है कि **Frontend (React) और Backend (FastAPI) दोनों एक ही सिंगल सर्विस पर चलते हैं**—यानी अलग-अलग डोमेन या CORS की कोई झंझट नहीं!

---

## 🌟 विकल्प 1: Render.com पर Free Deploy (सबसे आसान — सिर्फ 3 मिनट)

**Render** बिना क्रेडिट कार्ड के 100% फ्री डॉकर और वेब सर्विस होस्टिंग देता है।

### स्टेप्स:
1. **GitHub पर कोड पुश करें:**
   अगर आपने कोड GitHub पर नहीं डाला है, तो एक नया रिपॉजिटरी बनाकर पुश करें:
   ```bash
   git init
   git add .
   git commit -m "FormFix v2.0 Production Ready"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/formfix.git
   git push -u origin main
   ```

2. **Render पर जाएं:**
   - [render.com](https://render.com) खोलें और GitHub से लॉगिन करें।
   - **"New +"** बटन दबाएं और **"Web Service"** चुनें।
   - अपनी `formfix` रिपॉजिटरी सिलेक्ट करें।

3. **सेटिंग्स भरें:**
   - **Name:** `formfix` (या आपकी पसंद का नाम)
   - **Environment:** `Docker` (Render अपने आप हमारा `Dockerfile` डिटेक्ट कर लेगा)
   - **Instance Type:** `Free`
   - **"Create Web Service"** पर क्लिक करें!

4. **लाइव:** 3-4 मिनट में आपकी वेबसाइट लाइव हो जाएगी:
   👉 `https://formfix.onrender.com`

---

## 🌟 विकल्प 2: Railway.app पर 1-Click Deploy

Railway भी Dockerfile आधारित ऑटोमैटिक डिप्लॉयमेंट सपोर्ट करता है:

1. [railway.app](https://railway.app) पर जाएं।
2. **"New Project"** ➔ **"Deploy from GitHub repo"** चुनें।
3. अपनी रिपॉजिटरी चुनें।
4. Railway अपने आप `Dockerfile` को बिल्ड करेगा और आपको लाइव URL दे देगा।

---

## 🌟 विकल्प 3: Docker से अपने VPS / Cloud (AWS, DigitalOcean, GCP) पर चलाना

अगर आपके पास कोई Linux सर्वर (Ubuntu/Debian) या कंप्यूटर पर Docker है:

```bash
# 1. रिपॉजिटरी क्लोन करें
cd formsaathi

# 2. Docker Compose से 1 कमांड में चलाएं
docker compose up -d --build
```

आपका FormFix सर्वर तुरंत `http://localhost:8000` (या आपके सर्वर के पब्लिक IP पर) लाइव हो जाएगा!

---

## 🌟 विकल्प 4: Localhost पर Production Mode में चलाना

अगर आप अपने कंप्यूटर पर ही Production Build चलाकर देखना चाहते हैं:

```bash
# टर्मिनल 1:
cd c:\Users\hp\OneDrive\Desktop\formsaathi\backend
.venv\Scripts\activate
python -m uvicorn app.main:app --port 8000
```
अब ब्राउज़र में `http://localhost:8000` खोलें। 
FastAPI सीधे आपके React Frontend (`frontend/dist`) को सर्व करेगा और सारे APIs भी काम करेंगे!

---

## 🔒 Production Environment Variables (वैकल्पिक)

यदि आप प्रोडक्शन में कोई सेटिंग्स बदलना चाहें, तो ये एन्वायरनमेंट वैरिएबल्स सेट कर सकते हैं:

| Variable | Default Value | Description |
|---|---|---|
| `PORT` | `8000` | सर्वर पोर्ट नंबर |
| `DEMO_MODE_ENABLED` | `True` | हैकथॉन टेस्ट केस इनेबल रखने हेतु |
| `SECRET_KEY` | *(Auto-generated)* | सेशन और JWT सुरक्षा कुंजी |
| `SESSION_EXPIRE_MINUTES` | `30` | DPDP एक्ट के तहत 30 मिनट में डेटा डिलीट |
