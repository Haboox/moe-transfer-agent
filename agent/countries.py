"""Every country, in English and Arabic, for the nationality on the mock UAE Pass record in the open test.

The English name is what the record holds (and what rules.is_gcc reads); the Arabic name is shown on the Arabic page.
"""
from __future__ import annotations

COUNTRIES: dict[str, str] = {
    "Afghanistan": "أفغانستان", "Albania": "ألبانيا", "Algeria": "الجزائر", "Andorra": "أندورا", "Angola": "أنغولا",
    "Antigua and Barbuda": "أنتيغوا وباربودا", "Argentina": "الأرجنتين", "Armenia": "أرمينيا", "Australia": "أستراليا",
    "Austria": "النمسا", "Azerbaijan": "أذربيجان", "Bahamas": "جزر البهاما", "Bahrain": "البحرين",
    "Bangladesh": "بنغلاديش", "Barbados": "باربادوس", "Belarus": "بيلاروسيا", "Belgium": "بلجيكا", "Belize": "بليز",
    "Benin": "بنين", "Bhutan": "بوتان", "Bolivia": "بوليفيا", "Bosnia and Herzegovina": "البوسنة والهرسك",
    "Botswana": "بوتسوانا", "Brazil": "البرازيل", "Brunei": "بروناي", "Bulgaria": "بلغاريا",
    "Burkina Faso": "بوركينا فاسو", "Burundi": "بوروندي", "Cabo Verde": "الرأس الأخضر", "Cambodia": "كمبوديا",
    "Cameroon": "الكاميرون", "Canada": "كندا", "Central African Republic": "جمهورية أفريقيا الوسطى", "Chad": "تشاد",
    "Chile": "تشيلي", "China": "الصين", "Colombia": "كولومبيا", "Comoros": "جزر القمر", "Congo": "الكونغو",
    "Costa Rica": "كوستاريكا", "Côte d'Ivoire": "ساحل العاج", "Croatia": "كرواتيا", "Cuba": "كوبا", "Cyprus": "قبرص",
    "Czechia": "التشيك", "Democratic Republic of the Congo": "جمهورية الكونغو الديمقراطية", "Denmark": "الدنمارك",
    "Djibouti": "جيبوتي", "Dominica": "دومينيكا", "Dominican Republic": "جمهورية الدومينيكان", "Ecuador": "الإكوادور",
    "Egypt": "مصر", "El Salvador": "السلفادور", "Equatorial Guinea": "غينيا الاستوائية", "Eritrea": "إريتريا",
    "Estonia": "إستونيا", "Eswatini": "إسواتيني", "Ethiopia": "إثيوبيا", "Fiji": "فيجي", "Finland": "فنلندا",
    "France": "فرنسا", "Gabon": "الغابون", "Gambia": "غامبيا", "Georgia": "جورجيا", "Germany": "ألمانيا",
    "Ghana": "غانا", "Greece": "اليونان", "Grenada": "غرينادا", "Guatemala": "غواتيمالا", "Guinea": "غينيا",
    "Guinea-Bissau": "غينيا بيساو", "Guyana": "غيانا", "Haiti": "هايتي", "Honduras": "هندوراس", "Hungary": "المجر",
    "Iceland": "آيسلندا", "India": "الهند", "Indonesia": "إندونيسيا", "Iran": "إيران", "Iraq": "العراق",
    "Ireland": "أيرلندا", "Italy": "إيطاليا", "Jamaica": "جامايكا", "Japan": "اليابان", "Jordan": "الأردن",
    "Kazakhstan": "كازاخستان", "Kenya": "كينيا", "Kiribati": "كيريباتي", "Kosovo": "كوسوفو", "Kuwait": "الكويت",
    "Kyrgyzstan": "قيرغيزستان", "Laos": "لاوس", "Latvia": "لاتفيا", "Lebanon": "لبنان", "Lesotho": "ليسوتو",
    "Liberia": "ليبيريا", "Libya": "ليبيا", "Liechtenstein": "ليختنشتاين", "Lithuania": "ليتوانيا",
    "Luxembourg": "لوكسمبورغ", "Madagascar": "مدغشقر", "Malawi": "مالاوي", "Malaysia": "ماليزيا",
    "Maldives": "جزر المالديف", "Mali": "مالي", "Malta": "مالطا", "Marshall Islands": "جزر مارشال",
    "Mauritania": "موريتانيا", "Mauritius": "موريشيوس", "Mexico": "المكسيك", "Micronesia": "ميكرونيزيا",
    "Moldova": "مولدوفا", "Monaco": "موناكو", "Mongolia": "منغوليا", "Montenegro": "الجبل الأسود", "Morocco": "المغرب",
    "Mozambique": "موزمبيق", "Myanmar": "ميانمار", "Namibia": "ناميبيا", "Nauru": "ناورو", "Nepal": "نيبال",
    "Netherlands": "هولندا", "New Zealand": "نيوزيلندا", "Nicaragua": "نيكاراغوا", "Niger": "النيجر",
    "Nigeria": "نيجيريا", "North Korea": "كوريا الشمالية", "North Macedonia": "مقدونيا الشمالية", "Norway": "النرويج",
    "Oman": "عُمان", "Pakistan": "باكستان", "Palau": "بالاو", "Palestine": "فلسطين", "Panama": "بنما",
    "Papua New Guinea": "بابوا غينيا الجديدة", "Paraguay": "باراغواي", "Peru": "بيرو", "Philippines": "الفلبين",
    "Poland": "بولندا", "Portugal": "البرتغال", "Qatar": "قطر", "Romania": "رومانيا", "Russia": "روسيا",
    "Rwanda": "رواندا", "Saint Kitts and Nevis": "سانت كيتس ونيفيس", "Saint Lucia": "سانت لوسيا",
    "Saint Vincent and the Grenadines": "سانت فنسنت والغرينادين", "Samoa": "ساموا", "San Marino": "سان مارينو",
    "Sao Tome and Principe": "ساو تومي وبرينسيب", "Saudi Arabia": "السعودية", "Senegal": "السنغال", "Serbia": "صربيا",
    "Seychelles": "سيشل", "Sierra Leone": "سيراليون", "Singapore": "سنغافورة", "Slovakia": "سلوفاكيا",
    "Slovenia": "سلوفينيا", "Solomon Islands": "جزر سليمان", "Somalia": "الصومال", "South Africa": "جنوب أفريقيا",
    "South Korea": "كوريا الجنوبية", "South Sudan": "جنوب السودان", "Spain": "إسبانيا", "Sri Lanka": "سريلانكا",
    "Sudan": "السودان", "Suriname": "سورينام", "Sweden": "السويد", "Switzerland": "سويسرا", "Syria": "سوريا",
    "Taiwan": "تايوان", "Tajikistan": "طاجيكستان", "Tanzania": "تنزانيا", "Thailand": "تايلاند",
    "Timor-Leste": "تيمور الشرقية", "Togo": "توغو", "Tonga": "تونغا", "Trinidad and Tobago": "ترينيداد وتوباغو",
    "Tunisia": "تونس", "Turkey": "تركيا", "Turkmenistan": "تركمانستان", "Tuvalu": "توفالو", "Uganda": "أوغندا",
    "Ukraine": "أوكرانيا", "United Arab Emirates": "الإمارات العربية المتحدة", "United Kingdom": "المملكة المتحدة",
    "United States": "الولايات المتحدة", "Uruguay": "الأوروغواي", "Uzbekistan": "أوزبكستان", "Vanuatu": "فانواتو",
    "Vatican City": "الفاتيكان", "Venezuela": "فنزويلا", "Vietnam": "فيتنام", "Yemen": "اليمن", "Zambia": "زامبيا",
    "Zimbabwe": "زيمبابوي",
}


def names(lang: str) -> list[str]:
    """English keys, in alphabetical order of the name shown in that language."""
    return sorted(COUNTRIES, key=(lambda k: COUNTRIES[k]) if lang == "ar" else (lambda k: k))


def shown(key: str, lang: str) -> str:
    return COUNTRIES.get(key, key) if lang == "ar" else key
