"""
:::comment::: Management command to seed all Telangana state colleges into the DB.
Covers: Osmania, JNTU-H, Kakatiya, Telangana University, OU PG Centres,
        Hyderabad University, Mahatma Gandhi, Palamuru, Satavahana universities
        + prominent autonomous / private engineering, medical, law, arts colleges.
Run:  python manage.py seed_telangana_colleges
      python manage.py seed_telangana_colleges --truncate   (wipe & re-seed)
"""

from django.core.management.base import BaseCommand
from accounts.models import College

# :::comment::: Comprehensive Telangana college list grouped by district / university
TELANGANA_COLLEGES = [
    # ── HYDERABAD – OSMANIA UNIVERSITY ───────────────────────────────────────
    {"college_code": "OU001",     "college_name": "Osmania University College of Engineering",                   "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "OU002",     "college_name": "University College of Science, Osmania University",           "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "OU003",     "college_name": "University College of Arts & Social Sciences, OU",            "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "OU004",     "college_name": "University College of Commerce & Business Management, OU",    "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "OU005",     "college_name": "University College of Technology, Osmania University",        "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "OU006",     "college_name": "University College of Law, Osmania University",               "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "OU007",     "college_name": "University College of Pharmaceutical Sciences, OU",           "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "NIZAM001",  "college_name": "Nizam College",                                               "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "VASAVI001", "college_name": "Vasavi College of Engineering",                               "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "MJCET001",  "college_name": "Muffakham Jah College of Engineering & Technology",           "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "WOMEN_KOTI001","college_name":"Government Degree College for Women (Koti)",                "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "ST_ANN001", "college_name": "St. Ann's College for Women",                                 "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "AURORA_DC001","college_name":"Aurora's Degree & PG College",                               "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "CITY_HYD001","college_name": "City College Hyderabad",                                     "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "GDC_CHARMINAR001","college_name":"Government Degree College, Charminar",                   "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "GDC_AMEERPET001","college_name":"Government Degree College, Ameerpet",                     "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "GDC_MEHDIPATNAM001","college_name":"Government Degree College for Women, Mehdipatnam",     "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "GDC_RAMANTHAPUR001","college_name":"Government Degree College, Ramanthapur",               "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "GDC_KUKATPALLY001","college_name":"Government Degree College, Kukatpally",                 "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "GDC_PANJAGUTTA001","college_name":"Government Degree College, Panjagutta",                 "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "GDC_UPPAL001","college_name": "Government Degree College, Uppal",                          "university_name": "Osmania University",                     "district": "Medchal"},
    {"college_code": "GDC_MALKAJGIRI001","college_name":"Government Degree College, Malkajgiri",                 "university_name": "Osmania University",                     "district": "Medchal"},
    {"college_code": "GDC_LB_NAGAR001","college_name":"Government Degree College, LB Nagar",                     "university_name": "Osmania University",                     "district": "Rangareddy"},
    {"college_code": "OU_LAW001", "college_name": "Government Law College, Hyderabad",                           "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "CHAITANYA_LAW001","college_name":"Chaitanya Law College",                                   "university_name": "Osmania University",                     "district": "Hyderabad"},
    # ── HYDERABAD – JNTU-H ───────────────────────────────────────────────────
    {"college_code": "JNTUH001",  "college_name": "JNTU Hyderabad (Main Campus)",                                "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "JNTUH_CEH001","college_name":"JNTUH College of Engineering Hyderabad",                     "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "CBIT001",   "college_name": "Chaitanya Bharathi Institute of Technology (CBIT)",           "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "MVSR001",   "college_name": "MVSR Engineering College",                                    "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "METHODIST001","college_name":"Methodist College of Engineering & Technology",               "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "VNRVJIET001","college_name": "VNR Vignana Jyothi Institute of Engineering & Technology",   "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "GRIET001",  "college_name": "Gokaraju Rangaraju Institute of Engineering & Technology",    "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "STANLEY001","college_name": "Stanley College of Engineering & Technology for Women",       "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "VJIT001",   "college_name": "Vidya Jyothi Institute of Technology",                        "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "MGIT001",   "college_name": "Mahatma Gandhi Institute of Technology",                      "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "MJCETENG001","college_name":"MJCET Engineering College Annex",                             "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "JBIET001",  "college_name": "J B Institute of Engineering & Technology",                   "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "KESHAV001", "college_name": "Keshav Memorial Institute of Technology",                     "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "MATRUSRI001","college_name": "Matrusri Engineering College",                               "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "LORDS001",  "college_name": "Lords Institute of Engineering & Technology",                 "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "SWEC001",   "college_name": "Sridevi Women's Engineering College",                         "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "VIGNAN_HYD001","college_name":"Vignan's Institute of Information Technology",              "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "MLRIT001",  "college_name": "MLR Institute of Technology",                                  "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "TKR_CE001", "college_name": "TKR College of Engineering & Technology",                     "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "PACE001",   "college_name": "P A College of Engineering",                                   "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "SIET001",   "college_name": "Sreyas Institute of Engineering & Technology",                 "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "AURORA_ENG001","college_name":"Aurora's Engineering College",                               "university_name": "JNTU Hyderabad",                         "district": "Rangareddy"},
    {"college_code": "VARDHAMAN001","college_name":"Vardhaman College of Engineering",                            "university_name": "JNTU Hyderabad",                         "district": "Rangareddy"},
    {"college_code": "SRI_INDU001","college_name": "Sri Indu College of Engineering & Technology",               "university_name": "JNTU Hyderabad",                         "district": "Rangareddy"},
    {"college_code": "CVR001",    "college_name": "CVR College of Engineering",                                   "university_name": "JNTU Hyderabad",                         "district": "Rangareddy"},
    # ── MEDCHAL ──────────────────────────────────────────────────────────────
    {"college_code": "MALLA_MEC001","college_name":"Malla Reddy Engineering College",                            "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "MRECW001",  "college_name": "Malla Reddy Engineering College for Women",                   "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "MRCET001",  "college_name": "Malla Reddy College of Engineering & Technology (MRCET)",     "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "MRCEW001",  "college_name": "Malla Reddy College of Engineering for Women",                "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "KGRCET001", "college_name": "KG Reddy College of Engineering & Technology",                "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "CMR001",    "college_name": "CMR College of Engineering & Technology",                     "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "CMRIT001",  "college_name": "CMR Institute of Technology",                                  "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "CMRTC001",  "college_name": "CMR Technical Campus",                                        "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "ACE001",    "college_name": "ACE Engineering College",                                      "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "NGIT001",   "college_name": "Nalla Malla Reddy Engineering College",                       "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "HITAM001",  "college_name": "Hyderabad Institute of Technology and Management (HITAM)",    "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "CHRISTU001","college_name": "Christu Jyoti Institute of Technology & Science",             "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "SREENIDHI001","college_name":"Sreenidhi Institute of Science & Technology",                "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "KMM001",    "college_name": "KMM Institute of Technology & Science",                       "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "PALLAVI001","college_name": "Pallavi Engineering College",                                  "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "GEETHANJALI001","college_name":"Geethanjali College of Engineering & Technology",           "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "IARE001",   "college_name": "Institute of Aeronautical Engineering",                        "university_name": "JNTU Hyderabad",                         "district": "Medchal"},
    {"college_code": "MALLA_MED001","college_name":"Malla Reddy Institute of Medical Sciences",                  "university_name": "Kaloji NRU Health Sciences",              "district": "Medchal"},
    # ── MEDAK / SANGAREDDY ────────────────────────────────────────────────────
    {"college_code": "BVRIT001",  "college_name": "B V Raju Institute of Technology",                            "university_name": "JNTU Hyderabad",                         "district": "Medak"},
    {"college_code": "BVRIT_N001","college_name": "B V Raju Institute of Technology Narsapur",                   "university_name": "JNTU Hyderabad",                         "district": "Medak"},
    {"college_code": "JNTUH_SULTAN001","college_name":"JNTUH College of Engineering Sultanpur",                  "university_name": "JNTU Hyderabad",                         "district": "Medak"},
    {"college_code": "GDC_MEDAK001","college_name": "Government Degree College, Medak",                          "university_name": "Osmania University",                     "district": "Medak"},
    {"college_code": "GDC_SANGAREDDY001","college_name":"Government Degree College, Sangareddy",                 "university_name": "Osmania University",                     "district": "Sangareddy"},
    {"college_code": "GOVT_ENGG_SANGAREDDY001","college_name":"Government Engineering College Sangareddy",       "university_name": "JNTU Hyderabad",                         "district": "Sangareddy"},
    {"college_code": "GDC_ZAHEERABAD001","college_name":"Government Degree College, Zaheerabad",                 "university_name": "Osmania University",                     "district": "Sangareddy"},
    {"college_code": "WOXSEN001", "college_name": "Woxsen University",                                           "university_name": "Woxsen University",                      "district": "Sangareddy"},
    {"college_code": "IITH001",   "college_name": "IIT Hyderabad",                                               "university_name": "IIT Hyderabad",                          "district": "Sangareddy"},
    # ── SPECIAL / CENTRAL / DEEMED ────────────────────────────────────────────
    {"college_code": "BITS_HYD001","college_name":"BITS Pilani Hyderabad Campus",                                "university_name": "BITS Pilani",                            "district": "Rangareddy"},
    {"college_code": "IIIT_HYD001","college_name":"IIIT Hyderabad",                                              "university_name": "IIIT Hyderabad",                         "district": "Hyderabad"},
    {"college_code": "UOH001",    "college_name": "University of Hyderabad",                                     "university_name": "University of Hyderabad",                "district": "Hyderabad"},
    {"college_code": "EFLU001",   "college_name": "The English and Foreign Languages University (EFLU)",          "university_name": "EFLU",                                   "district": "Hyderabad"},
    {"college_code": "NALSAR001", "college_name": "NALSAR University of Law",                                    "university_name": "NALSAR",                                 "district": "Hyderabad"},
    {"college_code": "NIFT_HYD001","college_name":"NIFT Hyderabad",                                              "university_name": "NIFT",                                   "district": "Hyderabad"},
    {"college_code": "ICFAI001",  "college_name": "ICFAI Foundation for Higher Education (IFHE)",                "university_name": "ICFAI University",                       "district": "Hyderabad"},
    {"college_code": "MAHINDRA001","college_name": "Mahindra University",                                        "university_name": "Mahindra University",                    "district": "Hyderabad"},
    {"college_code": "ANURAG001", "college_name": "Anurag University",                                           "university_name": "Anurag University",                      "district": "Hyderabad"},
    {"college_code": "JNAFAU001", "college_name": "Jawaharlal Nehru Architecture & Fine Arts University",        "university_name": "JNAFAU",                                 "district": "Hyderabad"},
    # ── MEDICAL – HYDERABAD ───────────────────────────────────────────────────
    {"college_code": "OSMANIA_MED001","college_name":"Osmania Medical College",                                  "university_name": "Kaloji NRU Health Sciences",              "district": "Hyderabad"},
    {"college_code": "NIMS001",   "college_name": "Nizam's Institute of Medical Sciences (NIMS)",                "university_name": "Kaloji NRU Health Sciences",              "district": "Hyderabad"},
    {"college_code": "GANDHI_MED001","college_name":"Gandhi Medical College",                                    "university_name": "Kaloji NRU Health Sciences",              "district": "Hyderabad"},
    {"college_code": "DECCAN_MED001","college_name":"Deccan College of Medical Sciences",                        "university_name": "Kaloji NRU Health Sciences",              "district": "Hyderabad"},
    {"college_code": "KIMS_HYD001","college_name": "Krishna Institute of Medical Sciences (KIMS) Hyderabad",    "university_name": "Kaloji NRU Health Sciences",              "district": "Hyderabad"},
    {"college_code": "CARE_DENT001","college_name":"Care Dental College",                                        "university_name": "Kaloji NRU Health Sciences",              "district": "Hyderabad"},
    {"college_code": "GOVT_DENT001","college_name":"Government Dental College and Hospital Hyderabad",           "university_name": "Kaloji NRU Health Sciences",              "district": "Hyderabad"},
    {"college_code": "GOVT_NURSING001","college_name":"Government College of Nursing Hyderabad",                 "university_name": "Kaloji NRU Health Sciences",              "district": "Hyderabad"},
    {"college_code": "OU_PHARM001","college_name": "Osmania University College of Pharmaceutical Sciences",      "university_name": "Osmania University",                     "district": "Hyderabad"},
    {"college_code": "GOVT_PHARM001","college_name":"Government College of Pharmacy Hyderabad",                  "university_name": "Telangana State Board of Pharmacy",      "district": "Hyderabad"},
    {"college_code": "SV_PHARM001","college_name": "Sri Venkateshwara College of Pharmacy",                      "university_name": "JNTU Hyderabad",                         "district": "Hyderabad"},
    # ── WARANGAL ─────────────────────────────────────────────────────────────
    {"college_code": "NITW001",   "college_name": "NIT Warangal",                                                "university_name": "NIT Warangal",                           "district": "Hanamkonda"},
    {"college_code": "KU_ENG001", "college_name": "Kakatiya University College of Engineering",                  "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "KU_SCI001", "college_name": "University College of Science, Kakatiya University",          "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "KU_ARTS001","college_name": "Post Graduate College, Kakatiya University",                  "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "KU_LAW001", "college_name": "Kakatiya University Law College",                             "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "UCE_WGL001","college_name": "University College of Engineering Warangal (UCE)",            "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "KITS001",   "college_name": "Kakatiya Institute of Technology and Science",                 "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "KCE001",    "college_name": "Kakatiya College of Engineering",                             "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "SREC_WGL001","college_name":"SR Engineering College, Warangal",                            "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "GOVT_WOMEN_WGL001","college_name":"Government Degree & PG College for Women, Warangal",   "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "GOVT_CITY_WGL001","college_name":"Government City College, Warangal",                      "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    {"college_code": "KMC001",    "college_name": "Kakatiya Medical College",                                    "university_name": "Kaloji NRU Health Sciences",              "district": "Hanamkonda"},
    {"college_code": "MGM_WGL001","college_name": "Mahatma Gandhi Memorial Hospital & College",                  "university_name": "Kaloji NRU Health Sciences",              "district": "Hanamkonda"},
    {"college_code": "VAAGDEVI_PHARM001","college_name":"Vaagdevi College of Pharmacy",                          "university_name": "Kakatiya University",                    "district": "Hanamkonda"},
    # ── KARIMNAGAR / SATAVAHANA UNIVERSITY ───────────────────────────────────
    {"college_code": "SATAVAHANA_U001","college_name":"Satavahana University College",                           "university_name": "Satavahana University",                  "district": "Karimnagar"},
    {"college_code": "SATAVAHANA_E001","college_name":"Satavahana University College of Engineering",            "university_name": "Satavahana University",                  "district": "Karimnagar"},
    {"college_code": "GDC_KMR001","college_name": "Government Degree College, Karimnagar",                       "university_name": "Satavahana University",                  "district": "Karimnagar"},
    {"college_code": "GOVT_ARTS_KMR001","college_name":"Government Arts & Science College, Karimnagar",          "university_name": "Satavahana University",                  "district": "Karimnagar"},
    {"college_code": "SV_ENGG_KMR001","college_name":"Sree Venkateswara Engineering College Karimnagar",         "university_name": "Satavahana University",                  "district": "Karimnagar"},
    {"college_code": "SAMSKRUTI001","college_name":"Samskruti College of Engineering & Technology",              "university_name": "Satavahana University",                  "district": "Karimnagar"},
    # ── JAGTIAL ───────────────────────────────────────────────────────────────
    {"college_code": "JNTUH_KDG001","college_name":"JNTUH College of Engineering Kondagattu",                   "university_name": "JNTU Hyderabad",                         "district": "Jagtial"},
    {"college_code": "JNTUH_JGT001","college_name":"JNTUH College of Engineering Jagtial",                      "university_name": "JNTU Hyderabad",                         "district": "Jagtial"},
    {"college_code": "GDC_JAGTIAL001","college_name":"Government Degree College, Jagtial",                       "university_name": "Satavahana University",                  "district": "Jagtial"},
    {"college_code": "GDC_METPALLY001","college_name":"Government Degree College, Metpally",                     "university_name": "Satavahana University",                  "district": "Jagtial"},
    # ── PEDDAPALLI / RAMAGUNDAM ───────────────────────────────────────────────
    {"college_code": "GDC_PEDDAPALLI001","college_name":"Government Degree College, Peddapalli",                 "university_name": "Satavahana University",                  "district": "Peddapalli"},
    {"college_code": "GDC_RAMAGUNDAM001","college_name":"Government Degree College, Ramagundam",                 "university_name": "Satavahana University",                  "district": "Peddapalli"},
    {"college_code": "GDC_GODAVARIKHANI001","college_name":"Government Degree College, Godavarikhani",           "university_name": "Satavahana University",                  "district": "Peddapalli"},
    {"college_code": "JNTUH_MANTHANI001","college_name":"JNTUH College of Engineering Manthani",                 "university_name": "JNTU Hyderabad",                         "district": "Peddapalli"},
    # ── SIDDIPET ──────────────────────────────────────────────────────────────
    {"college_code": "GDC_SIDDIPET001","college_name":"Government Degree College, Siddipet",                    "university_name": "Satavahana University",                  "district": "Siddipet"},
    {"college_code": "GOVT_ENGG_SIDDIPET001","college_name":"Government Engineering College Siddipet",           "university_name": "JNTU Hyderabad",                         "district": "Siddipet"},
    {"college_code": "GDC_HUSNABAD001","college_name":"Government Degree College, Husnabad",                     "university_name": "Satavahana University",                  "district": "Siddipet"},
    {"college_code": "GDC_GAJWEL001","college_name":"Government Degree College, Gajwel",                        "university_name": "Satavahana University",                  "district": "Siddipet"},
    # ── NIZAMABAD / TELANGANA UNIVERSITY ─────────────────────────────────────
    {"college_code": "TU001",     "college_name": "Telangana University College (Main Campus)",                  "university_name": "Telangana University",                   "district": "Nizamabad"},
    {"college_code": "TU_SCI001", "college_name": "Telangana University College of Science",                     "university_name": "Telangana University",                   "district": "Nizamabad"},
    {"college_code": "TU_ARTS001","college_name": "Telangana University College of Arts",                        "university_name": "Telangana University",                   "district": "Nizamabad"},
    {"college_code": "GDC_NZB001","college_name": "Government Degree College, Nizamabad",                        "university_name": "Telangana University",                   "district": "Nizamabad"},
    {"college_code": "GDC_BODHAN001","college_name":"Government Degree College, Bodhan",                         "university_name": "Telangana University",                   "district": "Nizamabad"},
    {"college_code": "GDC_ARMOOR001","college_name":"Government Degree College, Armoor",                         "university_name": "Telangana University",                   "district": "Nizamabad"},
    {"college_code": "GOVT_ENGG_NZB001","college_name":"Government Engineering College Nizamabad",               "university_name": "JNTU Hyderabad",                         "district": "Nizamabad"},
    {"college_code": "GOVT_ARTS_NZB001","college_name":"Government Arts & Science College, Nizamabad",           "university_name": "Telangana University",                   "district": "Nizamabad"},
    # ── KAMAREDDY ────────────────────────────────────────────────────────────
    {"college_code": "GDC_KAMAREDDY001","college_name":"Government Degree College, Kamareddy",                  "university_name": "Telangana University",                   "district": "Kamareddy"},
    {"college_code": "GDC_BANSWADA001","college_name":"Government Degree College, Banswada",                     "university_name": "Telangana University",                   "district": "Kamareddy"},
    # ── KHAMMAM ───────────────────────────────────────────────────────────────
    {"college_code": "GDC_KHAMMAM001","college_name":"Government Degree College, Khammam",                      "university_name": "Kakatiya University",                    "district": "Khammam"},
    {"college_code": "SRI_CHAIT_KHM001","college_name":"Sri Chaitanya Engineering College Khammam",             "university_name": "JNTU Hyderabad",                         "district": "Khammam"},
    {"college_code": "NARAYANA_KHM001","college_name":"Narayana Engineering College Khammam",                    "university_name": "JNTU Hyderabad",                         "district": "Khammam"},
    {"college_code": "SRIT_KHM001","college_name": "Srinivasa Ramanujan Institute of Technology Khammam",       "university_name": "JNTU Hyderabad",                         "district": "Khammam"},
    # ── BHADRADRI KOTHAGUDEM ──────────────────────────────────────────────────
    {"college_code": "GDC_KOTHAGUDEM001","college_name":"Government Degree College, Kothagudem",                "university_name": "Kakatiya University",                    "district": "Bhadradri Kothagudem"},
    {"college_code": "GDC_BHADRACHALAM001","college_name":"Government Degree College, Bhadrachalam",            "university_name": "Kakatiya University",                    "district": "Bhadradri Kothagudem"},
    {"college_code": "GDC_YELLANDU001","college_name":"Government Degree College, Yellandu",                     "university_name": "Kakatiya University",                    "district": "Bhadradri Kothagudem"},
    # ── JANGAON / MAHABUBABAD / MULUGU ───────────────────────────────────────
    {"college_code": "GDC_JANGAON001","college_name":"Government Degree College, Jangaon",                      "university_name": "Kakatiya University",                    "district": "Jangaon"},
    {"college_code": "GDC_MAHABUBABAD001","college_name":"Government Degree College, Mahabubabad",               "university_name": "Kakatiya University",                    "district": "Mahabubabad"},
    {"college_code": "GDC_MULUGU001","college_name":"Government Degree College, Mulugu",                         "university_name": "Kakatiya University",                    "district": "Mulugu"},
    # ── NALGONDA ──────────────────────────────────────────────────────────────
    {"college_code": "GDC_NALGONDA001","college_name":"Government Degree College, Nalgonda",                    "university_name": "Osmania University",                     "district": "Nalgonda"},
    {"college_code": "GOVT_ENGG_NALGONDA001","college_name":"Government Engineering College Nalgonda",           "university_name": "JNTU Hyderabad",                         "district": "Nalgonda"},
    {"college_code": "GDC_MIRYALAGUDA001","college_name":"Government Degree College, Miryalaguda",              "university_name": "Osmania University",                     "district": "Nalgonda"},
    {"college_code": "GDC_DEVARAKONDA001","college_name":"Government Degree College, Devarakonda",               "university_name": "Osmania University",                     "district": "Nalgonda"},
    {"college_code": "VIGNANITS001","college_name":"Vignan's ITS Deshmukhi",                                     "university_name": "JNTU Hyderabad",                         "district": "Nalgonda"},
    {"college_code": "PBRVITS001","college_name": "PBR Visvodaya Institute of Technology & Science",             "university_name": "JNTU Hyderabad",                         "district": "Nalgonda"},
    # ── SURYAPET / YADADRI ───────────────────────────────────────────────────
    {"college_code": "GDC_SURYAPET001","college_name":"Government Degree College, Suryapet",                    "university_name": "Osmania University",                     "district": "Suryapet"},
    {"college_code": "GOVT_ENGG_SURYAPET001","college_name":"Government Engineering College Suryapet",           "university_name": "JNTU Hyderabad",                         "district": "Suryapet"},
    {"college_code": "GDC_BHONGIR001","college_name":"Government Degree College, Bhongir",                       "university_name": "Osmania University",                     "district": "Yadadri Bhuvanagiri"},
    # ── MAHABUBNAGAR / PALAMURU UNIVERSITY ───────────────────────────────────
    {"college_code": "PALAMURU_U001","college_name":"Palamuru University College (Main Campus)",                  "university_name": "Palamuru University",                    "district": "Mahabubnagar"},
    {"college_code": "PALAMURU_E001","college_name":"Palamuru University College of Engineering",                 "university_name": "Palamuru University",                    "district": "Mahabubnagar"},
    {"college_code": "GDC_MBN001","college_name": "Government Degree College, Mahabubnagar",                     "university_name": "Palamuru University",                    "district": "Mahabubnagar"},
    {"college_code": "SRI_SAI_MBN001","college_name":"Sri Sai Institute of Technology & Science",                "university_name": "JNTU Hyderabad",                         "district": "Mahabubnagar"},
    {"college_code": "GDC_WANAPARTHY001","college_name":"Government Degree College, Wanaparthy",                 "university_name": "Palamuru University",                    "district": "Wanaparthy"},
    {"college_code": "GDC_SHADNAGAR001","college_name":"Government Degree College, Shadnagar",                   "university_name": "Palamuru University",                    "district": "Rangareddy"},
    {"college_code": "GDC_NAGARKURNOOL001","college_name":"Government Degree College, Nagarkurnool",             "university_name": "Palamuru University",                    "district": "Nagarkurnool"},
    {"college_code": "GDC_NARAYANPET001","college_name":"Government Degree College, Narayanpet",                 "university_name": "Palamuru University",                    "district": "Narayanpet"},
    {"college_code": "GDC_GADWAL001","college_name":"Government Degree College, Gadwal",                         "university_name": "Palamuru University",                    "district": "Jogulamba Gadwal"},
    # ── VIKARABAD ────────────────────────────────────────────────────────────
    {"college_code": "GDC_VIKARABAD001","college_name":"Government Degree College, Vikarabad",                   "university_name": "Osmania University",                     "district": "Vikarabad"},
    {"college_code": "GDC_TANDUR001","college_name":"Government Degree College, Tandur",                         "university_name": "Osmania University",                     "district": "Vikarabad"},
    # ── ADILABAD / NIRMAL / MANCHERIAL / KUMARAM BHEEM ───────────────────────
    {"college_code": "GDC_ADILABAD001","college_name":"Government Degree College, Adilabad",                     "university_name": "Telangana University",                   "district": "Adilabad"},
    {"college_code": "GOVT_ENGG_ADILABAD001","college_name":"Government Engineering College Adilabad",           "university_name": "JNTU Hyderabad",                         "district": "Adilabad"},
    {"college_code": "GDC_NIRMAL001","college_name":"Government Degree College, Nirmal",                         "university_name": "Telangana University",                   "district": "Nirmal"},
    {"college_code": "GDC_MANCHERIAL001","college_name":"Government Degree College, Mancherial",                 "university_name": "Satavahana University",                  "district": "Mancherial"},
    {"college_code": "GDC_ASIFABAD001","college_name":"Government Degree College, Kumaram Bheem Asifabad",       "university_name": "Telangana University",                   "district": "Kumaram Bheem Asifabad"},
    # ── IIIT BASAR (RGUKT) ────────────────────────────────────────────────────
    {"college_code": "RGUKT_BASAR001","college_name":"RGUKT IIIT Basar",                                         "university_name": "RGUKT",                                  "district": "Nirmal"},
    # ── JNTUH CONSTITUENT COLLEGES ────────────────────────────────────────────
    {"college_code": "JNTUH_SULTAN001","college_name":"JNTUH College of Engineering Sultanpur",                  "university_name": "JNTU Hyderabad",                         "district": "Medak"},
    {"college_code": "JNTUH_MANTHANI001","college_name":"JNTUH College of Engineering Manthani",                 "university_name": "JNTU Hyderabad",                         "district": "Peddapalli"},
    {"college_code": "JNTUH_KONDAGATTU001","college_name":"JNTUH College of Engineering Kondagattu",             "university_name": "JNTU Hyderabad",                         "district": "Jagtial"},
    {"college_code": "JNTUH_JAGITYAL001","college_name":"JNTUH College of Engineering Jagtial",                  "university_name": "JNTU Hyderabad",                         "district": "Jagtial"},
]


class Command(BaseCommand):
    help = "Seed all Telangana state colleges into the College table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete existing Telangana college records before seeding.",
        )

    def handle(self, *args, **options):
        # :::comment::: Optionally wipe existing Telangana records first
        if options["truncate"]:
            deleted, _ = College.objects.filter(state="Telangana").delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing Telangana college records."))

        created_count = 0
        updated_count = 0

        for entry in TELANGANA_COLLEGES:
            college, created = College.objects.update_or_create(
                college_code=entry["college_code"],
                defaults={
                    "college_name":   entry["college_name"],
                    "university_name": entry.get("university_name", ""),
                    "state":           "Telangana",
                    "district":        entry.get("district", ""),
                    "is_active":       True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        total = College.objects.filter(state="Telangana").count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding complete — Created: {created_count}, Updated: {updated_count}. "
                f"Total Telangana colleges in DB: {total}"
            )
        )
