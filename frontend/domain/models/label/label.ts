export class LabelItem {
  constructor(
    readonly id: number,
    readonly text: string,
    readonly meta: object,
    readonly prefixKey: string | null,
    readonly suffixKey: string | null,
    readonly backgroundColor: string,
    readonly textColor: string = '#ffffff',
  ) {}

  static create(
    text: string,
    meta: Object,
    prefixKey: string | null,
    suffixKey: string | null,
    backgroundColor: string,
  ): LabelItem {
    return new LabelItem(0, text, meta, prefixKey, suffixKey, backgroundColor)
  }
}
