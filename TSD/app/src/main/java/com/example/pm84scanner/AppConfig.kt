package com.example.pm84scanner

/**
 * Default traceability / xtrace values. Overridden by SharedPreferences after first edit.
 */
object AppConfig {
    const val DEFAULT_BASE_URL = "https://xtrace.aslbelgisi.uz"
    const val DEFAULT_API_KEY = "29510cc0-0597-423b-92a8-849c4e7ac581"
    const val DEFAULT_BUSINESS_PLACE_ID = 6273
    const val DEFAULT_MANUFACTURER_COUNTRY = "UZ"
    const val DEFAULT_IMPORT_MANUFACTURER_COUNTRY = "KR"
    const val DEFAULT_PRODUCT_GROUP = "water"

    const val AGGREGATION_CODE_MAX_LEN = 31
    const val RELEASE_TYPE = "PRODUCTION"
}
