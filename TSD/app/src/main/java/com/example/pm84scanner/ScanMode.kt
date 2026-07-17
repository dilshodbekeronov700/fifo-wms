package com.example.pm84scanner

/**
 * Skanerlash va API zanjiri rejimi. [MainActivity] Intent orqali tanlanadi.
 */
enum class ScanMode {
    /** L1: quti (01x) + birliklar (010), joriy barqaror mantiq. */
    L1_BOX_UNIT,

    /** Import > Transport: transport (00… 20) + birliklar; utilisation faqat birliklar; agregatsiya transport→child unit. */
    L1_IMPORT_TRANSPORT,

    /** L2: Latok/Paddon/Transport; utilisation (unit+box) → agg1 (box+unit) → agg2 (transport+box). */
    L2_THREE_TIER,

    /** L3: birinchi 00… — ota, keyingilar — transport / box / AIK child kodlar; faqat agregatsiya. */
    L3_TRANSPORT_CHAIN,

    /** Ishlab chiqarish: faqat Dona (010), limitda faqat utilisation. */
    PRODUCTION_UNIT_ONLY,
}

object ScanIntentExtras {
    const val SCAN_MODE = "scan_mode"
    /** Import menyudan Box (L1) — utilisation uchun releaseType va qat’iy kod formatlari. */
    const val FROM_IMPORT = "from_import"
    /** Check menyusi: [CheckKind] nomi. */
    const val CHECK_KIND = "check_kind"
}

enum class CheckKind {
    ANY,
    UNIT,
    BOX,
    TRANSPORT;

    companion object {
        fun fromRaw(raw: String?): CheckKind {
            if (raw.isNullOrBlank()) return ANY
            return try {
                valueOf(raw)
            } catch (_: IllegalArgumentException) {
                ANY
            }
        }
    }
}

fun parseScanMode(raw: String?): ScanMode {
    if (raw.isNullOrBlank()) return ScanMode.L1_BOX_UNIT
    return try {
        ScanMode.valueOf(raw)
    } catch (_: IllegalArgumentException) {
        ScanMode.L1_BOX_UNIT
    }
}
