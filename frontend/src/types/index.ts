export interface Option {
  id: number;
  name: string;
  price: number;
  description: string;
  active: boolean;
}

export interface Machine {
  id: number;
  code: string;
  name: string;
  price: number;
  category: string;
  description: string;
  active: boolean;
  model_name?: string;
  product_title?: string;
  price_currency?: string;
  options?: Option[];
  availableOptions?: Option[];
}

export interface QuotationForm {
  clientName: string;
  clientCuit: string;
  clientPhone: string;
  clientAddress: string;
  clientEmail: string;
  clientCompany: string;
  notes: string;
}

export interface AdminQuotation {
  id: number;
  machine_code: string;
  client_cuit: string;
  client_name: string;
  client_phone?: string | null;
  client_email?: string | null;
  client_company?: string | null;
  notes?: string | null;
  client_discount_percent: number;
  additional_discount_percent: number;
  total_discount_percent: number;
  original_price: number;
  final_price: number;
  options_data?: string | null;
  options_total?: number;
  is_deleted: boolean;
  deleted_at?: string | null;
  deleted_by?: string | null;
  created_at: string;
}
