/** LynkSurvey's rating after payment on a customer screen (NEW UPDATE 4, master blueprint 63.7; build section 3): one tap on a touch
 *  screen, the "Rate us" QR on a screen that only shows. Never required, never before the payment is confirmed. A small part of its
 *  own, so a customer display carries only this and not the whole people engine. */
import type { Icon, T } from "./shell.js";
import { newId } from "./emulator.js";
import { quickRating, rateUs } from "./peopleparts.js";

export type ApEmit = (type: string, payload: Record<string, unknown>, origin?: "device" | "server") => void;
export class AfterPay {
  readonly surveyId = newId();
  readonly deviceId = newId();
  afterPayment = true;
  constructor(private emit: ApEmit) {}
  rate(n: number, way: "pos" | "kiosk", language: string): boolean {
    if (!this.afterPayment || !Number.isInteger(n) || n < 1 || n > 5) return false;
    this.emit("SurveyAnswered", { answer_id: newId(), survey_id: this.surveyId, version: 1, way, device_id: this.deviceId, language, answers: [{ q: "after_payment", number: n }] });
    return true;
  }
}
/** The rating on the customer's screen after a confirmed payment: buttons on a touch screen, the QR on a screen that only shows. */
export function afterPaymentRating(h: { afterPayment: boolean }, touch: boolean, chosen: number | null, t: T, icon: Icon): string {
  if (!h.afterPayment) return "";
  return `<div class="ph-rate">${touch ? quickRating(t("ppl_rate_title"), chosen, t) : rateUs(icon, t)}</div>`;
}
