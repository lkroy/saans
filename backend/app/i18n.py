"""Hindi (hi) translations for the printable school bulletin.

English remains the default; ``translate_bulletin`` converts the user-facing
strings of a bulletin dict. Evidence/limitations stay in English (staff-facing).
"""

ACTION_LABEL_HI = {
    "clear": "सब ठीक है",
    "caution": "सावधानी बरतें",
    "indoor": "अंदर का दिन",
    "severe": "आपातकालीन दिवस",
}

HEADLINE_HI = {
    "clear": "सब ठीक है — सामान्य बाहरी कार्यक्रम।",
    "caution": "सावधानी — भारी बाहरी गतिविधि कम करें; संवेदनशील बच्चे अंदर रहें।",
    "indoor": "अंदर का दिन — पीटी और खेल अंदर कराएं।",
    "severe": "आपातकालीन दिवस — अंदर रहें, यात्रा में मास्क पहनें; ऑनलाइन कक्षाओं पर विचार करें।",
}

DETAIL_HI = {
    "clear": "हवा अच्छी/संतोषजनक है और अगले 6 घंटों में AQI 100 या उससे कम रहने का अनुमान है। सामान्य बाहरी कार्यक्रम रखें।",
    "caution": "हवा मध्यम है। भारी बाहरी गतिविधि कम करने पर विचार करें और संवेदनशील बच्चों को अंदर रखें; 6 घंटे के चरम स्तर पर नजर रखें।",
    "indoor": "हवा खराब या बहुत खराब है। पीटी और खेल अंदर कराने की योजना बनाएं।",
    "severe": "हवा बहुत खराब या उससे भी बदतर है। आपातकालीन अंदरूनी दिवस मानें: यात्रा में N95 मास्क और स्कूल बोर्ड की नीति के अनुसार ऑनलाइन कक्षाओं पर विचार करें।",
}

CHECKLIST_HI = {
    "clear": [
        "सामान्य बाहरी कार्यक्रम",
        "स्कूल का AQI सूचना पट्ट अपडेट रखें",
        "स्कूल गेट के पास नो-आइडलिंग नियम की याद दिलाएं",
    ],
    "caution": [
        "लगातार भारी बाहरी गतिविधि सीमित करने पर विचार करें",
        "संवेदनशील बच्चे (अस्थमा/एलर्जी) अंदर रह सकते हैं — उनकी स्वास्थ्य योजना का पालन करें",
        "लंबे खेल अभ्यास के लिए नीचे दिया गया सबसे साफ समय चुनें, यदि उपलब्ध हो",
        "बाहरी योजना तय करने से पहले 6 घंटे के पूर्वानुमान पर नजर रखें",
    ],
    "indoor": [
        "सुबह की पीटी और खेल अंदर कराने की योजना बनाएं",
        "प्रदूषण के चरम घंटों में खिड़कियां कम खोलें, कक्षा के वेंटिलेशन का ध्यान रखें",
        "यदि उपलब्ध हों तो कक्षाओं में एयर प्यूरीफायर चलाएं",
        "बाहर यात्रा के लिए मास्क की सलाह दें; भारी मेहनत से बचें",
    ],
    "severe": [
        "सभी बाहरी गतिविधियां स्थगित रखें; स्कूल बोर्ड की नीति के अनुसार ऑनलाइन कक्षाओं पर विचार करें",
        "यात्रा करने वाले सभी के लिए N95 मास्क की सलाह दें",
        "वेंटिलेशन और गर्मी की जरूरतों का ध्यान रखते हुए खिड़कियां कम खोलें",
        "सांस की शिकायतों पर नजर रखें; छात्र स्वास्थ्य योजना के अनुसार इन्हेलर उपलब्ध रखें",
    ],
}

WINDOW_LABEL_HI = {
    "Cleanest window today": "आज का सबसे साफ समय",
    "Another low-AQI spell": "एक और साफ अवधि",
}

STRINGS_HI = {
    "bulletin_title": "सुबह का वायु-सुरक्षा बुलेटिन",
    "todays_peak": "आज का चरम स्तर",
    "generated": "जारी",
    "checklist_title": "आज की कार्यसूची",
    "no_window": "स्कूल के समय में बाहर का कोई उपयुक्त समय नहीं",
    "indicative_note": "संकेतात्मक प्रति-घंटा AQI · मॉडल आधारित डेटा (Open-Meteo)। स्कूल कार्यालय के सूचना पट्ट पर लगाएं।",
    "disclaimer": ("सांस मॉडल आधारित वायु-गुणवत्ता डेटा पर योजना-संबंधी मार्गदर्शन देता है। "
                   "यह स्कूल बंद करने का आधिकारिक आदेश नहीं है और न ही चिकित्सकीय सलाह। "
                   "बंद करने के लिए अपने स्कूल बोर्ड और स्थानीय प्रशासन के निर्देशों का पालन करें।"),
}

DISCLAIMER_EN = (
    "Saans provides planning guidance based on modelled air-quality data. "
    "It is not an official school-closure order and not medical advice. "
    "Follow your school board and local authorities for closures, and students' "
    "doctors for health decisions."
)


def translate_bulletin(bulletin, lang):
    """Return a copy of ``bulletin`` with user-facing strings in ``lang``.

    Supported: "en" (unchanged), "hi". Unknown languages fall back to "en".
    """
    if (lang or "en").lower() != "hi":
        return dict(bulletin, lang="en")
    b = dict(bulletin)
    level = b.get("call", {}).get("level", "caution")
    b["call"] = {
        "level": level,
        "label": ACTION_LABEL_HI.get(level, level),
        "headline": HEADLINE_HI.get(level, ""),
        "detail": DETAIL_HI.get(level, ""),
    }
    b["checklist"] = list(CHECKLIST_HI.get(level, []))
    b["best_windows"] = [
        dict(w, label=WINDOW_LABEL_HI.get(w.get("label", ""), w.get("label", "")))
        for w in b.get("best_windows", [])
    ]
    if b.get("windows_note"):
        b["windows_note"] = STRINGS_HI["no_window"] + " (08:00–15:00 IST)"
    b["disclaimer"] = STRINGS_HI["disclaimer"]
    b["strings"] = dict(STRINGS_HI)
    b["lang"] = "hi"
    return b
