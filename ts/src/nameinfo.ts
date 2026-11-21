/** The one-line descriptions of every Lynk name (web/nameinfo, keys nma_<id>, and "What is {name}?"), in every language.
 *  A page that imports this module carries them (web/emulators/build_data.py DEEP_WORDS), so its launcher, search, name
 *  notes and LynkAssist can say what each product does in the screen's language; other pages show the plain word only
 *  (ts/src/names.ts aboutOf). */
export const NAME_INFO_KEYS = { question: "nmi_what_q", answer: "nmi_what_a" } as const;
