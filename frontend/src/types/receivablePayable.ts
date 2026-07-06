export type OpenItemType = "receivable" | "payable";
export type CounterpartyType = "customer" | "supplier";

export interface CounterpartyBalanceItem {
  counterparty_type: CounterpartyType;
  counterparty_code: string;
  counterparty_name: string;
  open_item_type: OpenItemType;
  currency: string;
  original_balance: string | number;
  base_balance: string | number;
  open_item_count: number;
}

export interface CounterpartyBalanceResponse {
  account_set_id: string;
  period: string;
  open_item_type: OpenItemType;
  total_base_balance: string | number;
  item_count: number;
  items: CounterpartyBalanceItem[];
}

export interface AgingBucket {
  bucket_code: string;
  day_from: number;
  day_to?: number | null;
  amount: string | number;
  open_item_count: number;
}

export interface CounterpartyAgingItem {
  counterparty_type: CounterpartyType;
  counterparty_code: string;
  counterparty_name: string;
  buckets: AgingBucket[];
  total_base_balance: string | number;
}

export interface CounterpartyAgingResponse {
  account_set_id: string;
  period: string;
  as_of_date: string;
  open_item_type: OpenItemType;
  buckets: AgingBucket[];
  items: CounterpartyAgingItem[];
  total_base_balance: string | number;
}
