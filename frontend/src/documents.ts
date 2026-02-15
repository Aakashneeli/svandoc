export type DocumentStatus = "queued" | "processing" | "review_required" | "completed" | "failed";

export type DocumentListItem = {
  id: string;
  filename: string;
  vendor: string;
  status: DocumentStatus;
  amountTotal: number;
  createdAt: string; // YYYY-MM-DD
};

export type DocumentFilterInput = {
  query: string;
  status: "all" | DocumentStatus;
  startDate: string;
  endDate: string;
};

export function filterDocuments(items: DocumentListItem[], filter: DocumentFilterInput): DocumentListItem[] {
  const query = filter.query.trim().toLowerCase();
  const fromDate = filter.startDate ? Date.parse(filter.startDate) : null;
  const toDate = filter.endDate ? Date.parse(filter.endDate) : null;

  return items.filter((item) => {
    if (filter.status !== "all" && item.status !== filter.status) {
      return false;
    }

    if (query) {
      const haystack = `${item.vendor} ${item.filename} ${item.id}`.toLowerCase();
      if (!haystack.includes(query)) {
        return false;
      }
    }

    const created = Date.parse(item.createdAt);
    if (fromDate !== null && created < fromDate) {
      return false;
    }
    if (toDate !== null && created > toDate) {
      return false;
    }
    return true;
  });
}
