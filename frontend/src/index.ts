export type SupportedDocumentType = "invoice" | "receipt";

export function isSupportedDocumentType(value: string): value is SupportedDocumentType {
    return value === "invoice" || value === "receipt";
}
