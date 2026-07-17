# Smartup API — to'liq ma'lumotnoma (Postman collection'dan avtomatik)

Manba: https://api.greenwhite.uz (collection 38039337/2sAXxP8Xzx, 459KB). Auth: collection-level HTTP **Basic** (login:password). Sanalar `dd.mm.yyyy`.

> Bu fayl Postman JSON'idan generatsiya qilingan (barcha endpoint + body + izoh). Qisqa qo'lda-tahrir ma'lumotnoma: `smartup_api_reference.md`.


### Documents › Sale › Order › Order / Import
- **POST** `/b/trade/txs/tdeal/order$import`
```json
{
  "order": [
    {
      "filial_code": "",
      "external_id": "",
      "deal_id": "1",
      "subfilial_code": "",
      "delivery_number": "1",
      "delivery_date": "03.09.21",
      "room_code": "100",
      "robot_code": "100",
      "deal_time": "02.09.21",
      "status": "A",
      "sales_manager_code": "100",
      "person_code": "100",
      "currency_code": "860",
      "owner_person_code": "",
      "van_code": "",
      "contract_code": "",
      "note": "",
      "self_shipment" : "",
      "delivery_address_short" : "",
      "delivery_address_full" : "",
      "marking_attaching_method" : "", 
      "invoice_number": "100",
      "expeditor_code": "",
      "payment_type_code": "",
      "order_products": [
        {
          "external_id": "",
          "product_unit_id": "",
          "inventory_kind": "G",
          "warehouse_code": "100",
          "product_code": "100",
          "serial_number": "",
          "card_code": "",
          "expiry_date": "",
          "on_balance": "",
          "order_quant": "10",
          "price_type_code": "777",
          "product_price": "",
          "margin_kind": "S",
          "margin_value": "",
          "margin_amount": "100",
          "vat_percent": ""
        }
      ],
      "order_gifts": [
        {
          "external_id": "",
          "product_unit_id": "",
          "inventory_kind": "",
          "warehouse_code": "",
          "product_code": "",
          "serial_number": "",
          "card_code": "",
          "expiry_date": "",
          "on_balance": "",
          "order_quant": ""
        }
      ],
      "order_actions": [
        {
          "external_id": "",
          "product_unit_id": "",
          "inventory_kind": "",
          "warehouse_code": "",
          "product_code": "",
          "serial_number": "",
          "card_code": "",
          "expiry_date": "",
          "on_balance": "",
          "order_quant": "",
          "bonus_id": ""
        }
      ],
      "order_consignments": [
        {
          "external_id": "",
          "consignment_unit_id": "",
          "consignment_date": "",
          "consignment_amount": ""   
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
Through this interface, the service uploads order data to the Smartup X from third party software. The interface supports bulk data ingestion in a single request. 
 Request 
 {
 "order": [
 {
 "filial_code": "",
 "external_id": "",
 "deal_id": "1",
 "subfilial_code": "",
 "delivery_number": "1",
 "delivery_date": "03.09.21",
 "room_code": "100",
 "robot_code": "100",
 "deal_time": "02.09.21",
 "status": "A",
 "sales_manager_code": "100",
 "person_code": "100",
 "currency_code": "860",
 "owner_person_code": "",
 "van_code": "",
 "contract_code": "",
 "note": "",
 "self_shipment" : "",
 "delivery_address_short" : "",
 "delivery_address_full" : "",
 "marking_attaching_method" : "", 
 "invoice_number": "100",
 "expeditor_code": "",
 "payment_type_code": "",
 "order_products": [
 {
 "external_id": "",
 "product_unit_id": "",
 "inventory_kind": "G",
 "warehouse_code": "100",
 "product_code": "100",
 "serial_number": "",
 "card_code": "",
 "expiry_date": "",
 "on_balance": "",
 "order_quant": "10",
 "price_type_code": "777",
 "product_price": "",
 "margin_kind": "S",
 "margin_value": "",
 "margin_amount": "100",
 "vat_percent": ""
 }
 ],
 "order_gifts": [
 {
 "external_id": "",
 "product_unit_id": "",
 "inventory_kind": "",
 "warehouse_code": "",
 "product_code": "",
 "serial_number": "",
 "card_code": "",
 "expiry_date": "",
 "on_balance": "",
 "order_quant": ""
 }
 ],
 "order_actions": [
 {
 "external_id": "",
 "product_unit_id": "",
 "inventory_kind": "",
 "warehouse_code": "",
 "product_code": "",
 "serial_number": "",
 "card_code": "",
 "expiry_date": "",
 "on_balance": "",
 "order_quant": "",
 "bonus_id": ""
 }
 ],
 "order_consignments": [
 {
 "external_id": "",
 "consignment_unit_id": "",
 "consignment_date": "",
 "consignment_amount": "" 
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 order 
 array 
 yes 
 Array with order data 
 filial_code 
 string 
 yes 
 Organization unique code 
 external_id 
 string 
 no 
 Order ID assigned by third party software 
 deal_id 
 number 
 no 
 The order ID is automatically assigned by the system 
 delivery_number 
 string 
 no 
 Invoice number 
 deal_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Order Acceptance Date 
 delivery_date 
 date(dd.mm.yyyy) 
 yes 
 Order delivery date 
 status 
 string 
 yes 
 Order status ( D - Draft, B#N - New, B#E - In progress, B#W - Wai
…(qisqartirildi)
```

### Documents › Sale › Order › Order / Export
- **POST** `/b/trade/txs/tdeal/order$export`
- Headers: `project_code: trade`, `filial_id: 1833`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "deal_id": "",
  "begin_deal_date": "",
  "end_deal_date": "",
  "delivery_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
Uploading data about orders for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "statuses":[""],
 "filial_code": "",
 "external_id": "",
 "deal_id": "",
 "begin_deal_date": "",
 "end_deal_date": "",
 "delivery_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": "",
 "producer_codes": [""]
}
 Response 
 {
 "order": [
 {
 "filial_code": "",
 "external_id": "",
 "deal_id": "",
 "invoice_external_id": "",
 "subfilial_code": "",
 "deal_time": "",
 "delivery_number": "", 
 "delivery_date": "",
 "booked_date": "",
 "total_amount": "",
 "room_id": "",
 "room_code": "", 
 "room_name": "",
 "robot_code": "",
 "lap_code": "",
 "sales_manager_id": "",
 "sales_manager_code": "",
 "sales_manager_name": "",
 "expeditor_id": "",
 "expeditor_code": "",
 "expeditor_name": "",
 "person_id": "",
 "person_code": "",
 "person_name": "",
 "person_local_code": "",
 "person_latitude": "",
 "person_longitude": "",
 "person_tin": "",
 "currency_code": "",
 "owner_person_code": "",
 "manager_code": "",
 "van_code": "",
 "contract_code": "",
 "contract_number": "",
 "invoice_number": "",
 "contract_code": "",
 "contract_number": "",
 "invoice_number": "",
 "payment_type_code": "",
 "deal_margin_kind": "",
 "deal_margin_value": "",
 "visit_payment_type_code": "",
 "note": "",
 "deal_note": "",
 "status": "",
 "with_marking": "",
 "self_shipment": "",
 "delivery_address_short": "",
 "delivery_address_full": "",
 "marking_attaching_method": "",
 "visit_id": "",
 "total_weight_netto": "",
 "total_weight_brutto": "",
 "total_litre": "",
 "order_products": [
 {
 "external_id": "",
 "product_unit_id": "",
 "product_code": "",
 "product_local_code": "",
 "product_name": "",
 "serial_number": "",
 "expiry_date": "",
 "order_quant": "",
 "sold_quant": "",
 "return_quant": "",
 "inventory_kind": "",
 "on_balance": "",
 "card_code": "",
 "warehouse_code": "",
 "product_price": "",
 "margin_amount": "",
 "margin_value": "",
 "margin_kind": "",
 "vat_amount": "",
 "vat_percent": "",
 "sold_amount": "",
 "price_type_code": "",
 "price_type_id": "",
 "details": [
 {
 "expiry_date": "",
 "card_code": "",
 "batch_number": "",
 "sold_quant": ""
 }
 ],
 "action_margins": [
 {
 "bonus_calc_level": "",
 "bonus_id": "",
 "margin_value": "",
 "margin_kind": "",
 "action_name": ""

…(qisqartirildi)
```

### Documents › Sale › Order › Order Attach Data
- **POST** `/b/trade/txs/tdeal/order$attach_data`
```json
{
    "order": [
        {
            "deal_id": "",
            "delivery_number": "",
            "expeditor_code": "",
            "van_code": "",
            "self_shipment": "",
            "note": "",
            "marking_attaching_method": ""
        }
    ]
}
```
**Izoh / sxema:**
```
This interface allows you to attach marking codes for order. 
 Request 
 {
 "order": [
 {
 "deal_id": "",
 "delivery_number": "",
 "expeditor_code": "",
 "van_code": "",
 "self_shipment": "",
 "note": "",
 "marking_attaching_method": ""
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 order 
 array 
 yes 
 Array containing data about orders 
 deal_id 
 number 
 yes 
 The order ID is automatically assigned by the system 
 delivery_number 
 string 
 no 
 Invoice number 
 expeditor_code 
 array 
 no 
 Expeditor code 
 van_code 
 string 
 no 
 State vehicle number 
 self_shipment 
 string 
 no 
 The status that determines weither the order is self shipped or not. (Y - yes, N - no) 
 note 
 string 
 no 
 Note 
 marking_attaching_method 
 string 
 no 
 A method of attaching marking codes to an order. (O - order, V - van) 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique record code 
 message 
 string 
 Clarifying error messages from the server
```

### Documents › Sale › Order › Order Status Change
- **POST** `/b/trade/txs/tdeal/order$change_status`
```json
{
  "order": [
      {
      "deal_id": "642",
      "status": "A"
      }
  ]
}
```
**Izoh / sxema:**
```
This interface allows you to change the status of orders. 
 Request 
 {
 "order": [
 {
 "deal_id": "642",
 "status": "A"
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 ]
}
 Discription of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 order 
 array 
 yes 
 Array with order data that is used to change status afterwards 
 deal_id 
 number 
 yes 
 Order ID 
 status 
 string 
 yes 
 Order status (Y - yes, N - no) 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique record code 
 message 
 string 
 Clarifying error messages from the server
```

### Documents › Sale › Order › Order Attach Marking Codes
- **POST** `/b/anor/mxsx/mdeal/order$import_order_marking_codes`
```json
{
    "deal_id": "",
    "products": [
        {
            "product_unit_id": "",
            "marking_codes": [""]
        }
    ]
}
```
**Izoh / sxema:**
```
This interface allows you to attach marking codes for order. 
 Request 
 {
 "deal_id": "",
 "products": [
 {
 "product_unit_id": "",
 "marking_codes": [""]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 deal_id 
 number 
 yes 
 Order ID in the Smartup system 
 products 
 array 
 yes 
 Array with data about of goods and materials in the order 
 product_unit_id 
 number 
 yes 
 Order Item ID 
 marking_codes 
 array 
 yes 
 Array with data of attaching marking codes for product unit 
 Desctiption of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique record code 
 message 
 string 
 Clarifying error messages from the server
```

### Documents › Sale › Return › Return / Import
- **POST** `/b/anor/mxsx/mdeal/return$import`
```json
{
  "return": [
    {
      "filial_code": "",
      "external_id": "",
      "deal_id": "",
      "subfilial_code": "",
      "order_deal_id": "",
      "delivery_number": "", 
      "delivery_date": "",
      "booked_date": "",
      "deal_time": "",
      "status": "",
      "sales_manager_code": "",
      "expeditor_code": "",
      "person_code": "",
      "currency_code": "",
      "owner_person_code": "",
      "manager_code": "",
      "van_code": "",
      "contract_code": "",
      "note": "",
      "return_reason_code": "",
      "invoice_number": "",
      "payment_type_code": "",
      "return_products": [
        {
          "external_id": "",
          "product_unit_id": "",
          "product_code": "",
          "serial_number": "",
          "card_code": "",
          "expiry_date": "",
          "return_quant": "",
          "product_price": "",
          "on_balance": "",
          "margin_kind": "",
          "margin_value": "",
          "vat_percent": "",
          "inventory_kind": "",
          "price_type_code": "",
          "warehouse_code": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
The interface allows you to upload data on order returns from third-party software to the Smartup X . This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "return": [
 {
 "filial_code": "",
 "external_id": "",
 "deal_id": "",
 "subfilial_code": "",
 "order_deal_id": "",
 "delivery_number": "", 
 "delivery_date": "",
 "booked_date": "",
 "room_code": "",
 "robot_code": "",
 "deal_time": "",
 "status": "",
 "sales_manager_code": "",
 "expeditor_code": "",
 "person_code": "",
 "currency_code": "",
 "owner_person_code": "",
 "manager_code": "",
 "van_code": "",
 "contract_code": "",
 "note": "",
 "return_reason_code": "",
 "invoice_number": "",
 "payment_type_code": "",
 "return_products": [
 {
 "external_id": "",
 "product_unit_id": "",
 "product_code": "100",
 "serial_number": "",
 "card_code": "",
 "expiry_date": "",
 "return_quant": "10",
 "product_price": "777",
 "on_balance": "",
 "margin_kind": "",
 "margin_value": "",
 "vat_percent": "",
 "inventory_kind": "G",
 "price_type_code": "777",
 "warehouse_code": "101"
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 return 
 array 
 yes 
 Array with order data 
 filial_code 
 string 
 optional 
 Organization unique code 
 external_id 
 string 
 optional 
 Order ID assigned by third party software 
 deal_id 
 number 
 optional 
 Order ID assigned by Smartup system 
 subfilial_code 
 string 
 no 
 Unique project code 
 order_deal_id 
 string 
 no 
 Order ID to which the order is being returned 
 delivery_number 
 string 
 no 
 Invoice number 
 deal_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Order return date 
 delivery_date 
 date(dd.mm.yyyy) 
 yes 
 Return delivery date 
 booked_date 
 date(dd.mm.yyyy) 
 no 
 Booking date 
 status 
 string 
 yes 
 Order status ( D - draft, A - archived) 
 room_code 
 string 
 yes 
 Unique workspace code, where the return was accepted 
 robot_code 
 string 
 yes 
 The unique code of the state where the return was accepted 
 sales_manager_code 
 string 
 yes 
 Unique manager code 
 forwarder_code 
 string 
 no 
 person_code 
 string 
 yes 
 Unique client code 
 currency_code 
 string 
 yes 
 Unique return currency code 
 expeditor_code 
 string 
 no 
 Expeditor code 
 warehouse_code 
 string 
 yes 
 Unique warehouse code for the return of goods and materials 
 contract_code 
 string 
 no 
 Unique co
…(qisqartirildi)
```

### Documents › Sale › Return › Return / Export
- **POST** `/b/anor/mxsx/mdeal/return$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "deal_id": "",
  "begin_return_date": "",
  "end_return_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports return data for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "deal_id": "",
 "begin_return_date": "",
 "end_return_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": "",
 "producer_codes": [""]
}
 Response 
 {
 "return": [
 {
 "filial_code": "",
 "external_id": "",
 "deal_id": "",
 "deal_time": "",
 "subfilial_code": "",
 "order_deal_id": "",
 "delivery_date": "",
 "delivery_number": "",
 "booked_date": "",
 "room_id": "",
 "room_code": "",
 "robot_code": "",
 "sales_manager_code": "",
 "sales_manager_name": "",
 "expeditor_code": "",
 "person_code": "",
 "person_id": "",
 "person_name": "",
 "person_tin": "",
 "owner_person_code": "",
 "van_code": "",
 "contract_code": "",
 "invoice_number": "",
 "batch_number": "",
 "payment_type_code": "",
 "note": "",
 "manager_code": "",
 "total_amount": "",
 "status": "",
 "return_reason_id": "",
 "return_reason_code": "",
 "currency_code": "",
 "return_products": [
 {
 "external_id": "",
 "product_unit_id": "",
 "product_code": "",
 "product_name": "",
 "expiry_date": "",
 "on_balance": "",
 "return_quant": "",
 "serial_number": "",
 "product_price": "",
 "margin_amount": "",
 "margin_kind": "",
 "margin_value": "",
 "card_code": "",
 "vat_percent": "",
 "vat_amount": "",
 "sold_amount": "",
 "inventory_kind": "",
 "price_type_code": "",
 "warehouse_code": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_codes 
 array 
 no 
 Array with data of organizations participating in the order (!) 
 filial_code 
 string 
 no 
 Unique code of the organization involved in the return process 
 external_id 
 string 
 no 
 Order ID assigned by third party software 
 deal_id 
 number 
 no 
 Order ID in the Smartup system 
 begin_return_date 
 date(dd.mm.yyyy) 
 no 
 Filter by return begin date 
 end_return_date 
 date(dd.mm.yyyy) 
 no 
 Filter by return end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 producer_codes 
 array/string 
 
…(qisqartirildi)
```

### Documents › Sale › Visit › Visit / Export
- **POST** `/b/trade/txs/tvt/visit$export`
- Headers: `project_code: trade`, `filial_id: 97675`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "visit_id": "",
  "external_id": "",
  "begin_visit_date": "",
  "end_visit_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on visits for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "visit_id": "",
 "external_id": "",
 "begin_visit_date": "",
 "end_visit_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": "",
 "user_id": "",
 "visit_status": "",
 "is_planned": "",
 "person_id": ""
}
 Response 
 {
 "visit":[
 {
 "visit_headers": [
 {
 "visit_id": "",
 "filial_code": "",
 "visit_date": "",
 "visit_start_time": "",
 "visit_end_time": "",
 "time_at_retail_outlet_sec": "",
 "person_name": "",
 "person_code": "",
 "person_id": "",
 "person_types": [
 {
 "person_type_id": "",
 "person_type_name": ""
 }
 ],
 "room_id": "",
 "room_name": "",
 "room_code": "",
 "supervisor_id": "",
 "sales_manager_id": "",
 "sales_manager_name": "",
 "sales_manager_code": "",
 "visit_start_location": "",
 "visit_end_location": "",
 "is_planned": "",
 "visit_status": ""
 }
 ],
 "stocks": [
 {
 "stock_product_code": "",
 "stock_quant": "",
 "stock_expiry_date": "",
 "stock_card_code": ""
 }
 ],
 "merchandisings": [
 {
 "merchandising_id": "",
 "assortment": [
 {
 "assortment_product_code": "",
 "has_assortment": "",
 "assortment_product_quant": "",
 "assortment_product_ir_quant": "",
 "assortment_unavail_reason_name": ""
 }
 ],
 "planograms": [
 {
 "planogram_id": "",
 "planogram_name": "",
 "planogram_has_photo": "",
 "planogram_photo_sha": "",
 "planogram_equipments": [
 {
 "planogram_equipment_id": "",
 "planogram_equipment_name": ""
 }
 ],
 "planogram_plan_quant": "",
 "planogram_plan_sku": "",
 "planogram_fact_quant": "",
 "planogram_fact_sku": "",
 "planogram_products": [
 {
 "planogram_product_name": "",
 "planogram_sample_unit_id": "",
 "planogram_product_code": "",
 "planogram_product_plan_quant": "",
 "planogram_product_fact_quant": "",
 "planogram_match": "",
 "planogram_match_face_quant": "",
 "planogram_not_match_reason_name": ""
 }
 ]
 }
 ],
 "shelf_shares": [
 {
 "own_shelf_shares": [
 {
 "own_shelf_share_product_code": "",
 "own_shelf_share_product_quant": ""
 }
 ],
 "competitor_inventories": [
 {
 "competitor_code": "",
 "competitor_inventory_product_code": "",
 "competitor_inventory_product_quant": ""
 }
 ]
 }
 ],
 "price_tags": [
 {
 "price_tag_product_code": "",
 "has_price_tag": "",
 "price": "",
 "no_price_ta
…(qisqartirildi)
```

### Documents › Warehouse › Cross-organizational movement › Cross-organizational Movement / Import
- **POST** `/b/anor/mxsx/mfm/movement$import`
```json
{
    "movement": [
        {
            "from_filial_code": "",
            "external_id": "",
            "movement_id": "",
            "subfilial_code": "",
            "to_subfilial_code": "",
            "from_room_code": "",
            "from_robot_code": "",
            "from_robot_person_code": "",
            "from_warehouse_code": "",
            "from_time": "",
            "to_filial_code": "",
            "to_warehouse_code": "",
            "to_time": "",
            "currency_code": "",
            "price_type_code": "",
            "payment_type_code": "",
            "cash_register_id": "",
            "request_id": "",
            "reason_id": "",
            "note": "",
            "barcode": "",
            "amount": "",
            "amount_base": "",
            "delivery_number": "",
            "contract_code": "",
            "status": "",
            "movement_items": [
                {
                    "external_id": "",
                    "movement_unit_id": "",
                    "request_item_id": "",
                    "from_inventory_kind": "",
                    "on_balance": "",
                    "to_inventory_kind": "",
                    "product_code": "",
                    "card_code": "",
                    "expiry_date": "",
                    "serial_number": "",
                    "quantity": "",
                    "price": "",
                    "amount": "",
                    "amount_base": "",
                    "margin_kind": "",
                    "margin_value": "",
                    "margin_amount": "",
                    "vat_percent": "",
                    "vat_amount": "",
                    "load_id": ""
                }
            ]
        }
    ]
}
```
**Izoh / sxema:**
```
This interface uploads cross-organization movements data to the Smartup X from third party software. The interface supports bulk data ingestion in a single request. 
 Request 
 {
 "movement": [
 {
 "from_filial_code": "",
 "external_id": "",
 "movement_id": "",
 "subfilial_code": "",
 "to_subfilial_code": "",
 "from_room_code": "",
 "from_robot_code": "",
 "from_robot_person_code": "",
 "from_warehouse_code": "",
 "from_time": "",
 "to_filial_code": "",
 "to_warehouse_code": "",
 "to_time": "",
 "currency_code": "",
 "price_type_code": "",
 "payment_type_code": "",
 "cash_register_id": "",
 "request_id": "",
 "reason_id": "",
 "note": "",
 "barcode": "",
 "amount": "",
 "amount_base": "",
 "delivery_number": "",
 "contract_code": "",
 "status": "",
 "movement_items": [
 {
 "external_id": "",
 "movement_unit_id": "",
 "request_item_id": "",
 "from_inventory_kind": "",
 "on_balance": "",
 "to_inventory_kind": "",
 "product_code": "",
 "card_code": "",
 "expiry_date": "",
 "serial_number": "",
 "quantity": "",
 "price": "",
 "amount": "",
 "amount_base": "",
 "margin_kind": "",
 "margin_value": "",
 "margin_amount": "",
 "vat_percent": "",
 "vat_amount": "",
 "load_id": ""
 }
 ]
 }
 ]
}
 Response 
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 movement 
 array 
 yes 
 Array with data on the interorganizational movement (information about the move itself) 
 filial_code 
 string 
 no 
 Organization code of searching movement 
 from_filial_code 
 string 
 yes 
 Organization of movement (sender) 
 external_id 
 string 
 no 
 Movement ID assigned by third party software 
 movement_id 
 number 
 no 
 Movement ID assigned by Smartup 
 subfilial_code 
 string 
 no 
 Project code 
 to_subfilial_code 
 string 
 no 
 Project code 
 from_room_code 
 string 
 yes 
 Workspace code (sender) 
 from_robot_code 
 string 
 yes 
 Staff Unit code (sender) 
 from_robot_person_code 
 string 
 yes 
 User code (sender) 
 from_warehouse_code 
 string 
 yes 
 Warehouse code (sender) 
 from_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Time of sending movement 
 to_filial_code 
 string 
 yes 
 Organization code (recipient) 
 to_warehouse_code 
 string 
 no 
 Warehouse code (recipient) 
 to_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 no 
 Time of receiving movement to another organization 
 currency_code 
 string 
 yes 
 Currency code 
 price_type_code 
 string 
 yes 
 P
…(qisqartirildi)
```

### Documents › Warehouse › Cross-organizational movement › Cross-organizational Movement / Export
- **POST** `/b/anor/mxsx/mfm/movement$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "movement_id": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on cross-organizational movements for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "movement_id": "",
 "begin_from_date": "",
 "end_from_date": "",
 "begin_to_date": "",
 "end_to_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "movement": [
 {
 "from_filial_code": "",
 "external_id": "",
 "movement_id": "",
 "subfilial_code": "",
 "to_subfilial_code": "",
 "from_room_code": "",
 "from_robot_code": "",
 "from_robot_person_code": "",
 "from_warehouse_code": "",
 "from_time": "",
 "to_filial_code": "",
 "to_warehouse_code": "",
 "to_time": "",
 "currency_code": "",
 "price_type_code": "",
 "payment_type_code": "",
 "to_payment_type_code": "",
 "request_id": "",
 "reason_id": "",
 "note": "",
 "barcode": "",
 "amount": "",
 "amount_base": "",
 "delivery_number": "",
 "contract_code": "",
 "status": "",
 "movement_items": [
 {
 "external_id": "",
 "movement_unit_id": "",
 "request_item_id": "",
 "from_inventory_kind": "",
 "on_balance": "",
 "to_inventory_kind": "",
 "product_code": "",
 "card_code": "",
 "expiry_date": "",
 "serial_number": "",
 "quantity": "",
 "price": "",
 "amount": "",
 "amount_base": "",
 "margin_kind": "",
 "margin_value": "",
 "margin_amount": "",
 "vat_percent": "",
 "vat_amount": "",
 "load_id": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Description 
 filial_codes 
 array 
 Array with data of organizations involved in the movement * 
 filial_code 
 string 
 Organization unique code 
 external_id 
 string 
 Movement ID assigned by third party software 
 movement_id 
 number 
 Movement ID assigned by Smartup 
 begin_from_date 
 date(dd.mm.yyyy) 
 Filter by movement begin date 
 end_from_date 
 date(dd.mm.yyyy) 
 Filter by movement end date 
 begin_to_date 
 date(dd.mm.yyyy) 
 Filter by receiving begin date 
 end_to_date 
 date(dd.mm.yyyy) 
 Filter by receiving end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 Filter by date of modification 
 end_modified_on 
 date (dd.mm.yyyy) 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
…(qisqartirildi)
```

### Documents › Warehouse › Cross-organizational movement › Cross-organizational Movement Status Change
- **POST** `/b/anor/mxsx/mfm/movement$change_status`
```json
{
  "movement": [
      {
      "movement_id" : "",
      "status": ""
      }
  ]
}
```
**Izoh / sxema:**
```
This interface allows you to change the status of cross-organizational movements. 
 Request 
 {
 "movement": [
 {
 "movement_id" : "",
 "status": ""
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 movement 
 array 
 yes 
 Array with movement data that is used to change status afterwards 
 movement_id 
 number 
 yes 
 Movement ID 
 status 
 string 
 yes 
 Movement status ( D - Draft N - New W - Waiting S - Sent A - Approved R - Returned C - Completed L - Cancelled) 
 Desctiption of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique record code 
 message 
 string 
 Clarifying error messages from the server
```

### Documents › Warehouse › Internal movement › Internal movement / Import
- **POST** `/b/anor/mxsx/mkw/movement$import`
```json
{
  "movement": [
    {
      "filial_code": "100",
      "external_id": "",
      "movement_id": "1",
      "request_id":"",
      "movement_number": "100",
      "from_movement_date": "",
      "to_movement_date": "",
      "status": "C",
      "from_warehouse_code": "100",
      "to_warehouse_code": "101",
      "reason_code": "",
      "note": "",
      "barcode": "",
      "movement_items": [
        {
          "external_id": "",
          "movement_item_id": "",
          "request_item_id": "",
          "product_code": "100",
          "inventory_kind": "G",
          "card_code": "",
          "serial_number": "",
          "expiry_date": "",
          "on_balance": "",
          "quantity": "1",
          "batch_number": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
Through this interface, the service uploads data on interorganizational movements to the Smartup system X from third party software. The interface supports bulk data ingestion in a single request. 
 Request 
 {
 "movement": [
 {
 "filial_code": "100",
 "external_id": "",
 "movement_id": "1",
 "request_id":"",
 "movement_number": "100",
 "from_movement_date": "",
 "to_movement_date": "",
 "status": "C",
 "from_warehouse_code": "100",
 "to_warehouse_code": "101",
 "reason_code": "",
 "note": "",
 "barcode": "",
 "movement_items": [
 {
 "external_id": "",
 "movement_item_id": "",
 "request_item_id": "",
 "product_code": "100",
 "inventory_kind": "G",
 "card_code": "",
 "serial_number": "",
 "expiry_date": "",
 "on_balance": "",
 "quantity": "1",
 "batch_number": "",
 "marking_codes": [
 {
 "marking_code": ""
 }
 ]
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 movement 
 array 
 yes 
 Array with data on the interorganizational movement (information about the move itself) 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Movement ID assigned by third party software 
 movement_id 
 number 
 no 
 Movement ID assigned by Smartup 
 request_id 
 number 
 no 
 Request ID for interorganizational movement 
 movement_number 
 string 
 no 
 Movement number 
 from_movement_date 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Shipping date of the inventories 
 to_movement_date 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Receiving date of the inventories 
 request_number 
 string 
 no 
 Move request number 
 form_warehouse_code 
 string 
 yes 
 Recipient's unique state code 
 to_warehouse_code 
 string 
 yes 
 The unique code of the consignee's warehouse 
 reason_code 
 string 
 no 
 The unique code of the sender's warehouse 
 barcode 
 string 
 no 
 A barcode is coded information applied to packaging in the form of strokes, read using special devices. With the help of a bar code, information about some of the most significant product parameters is encoded. The most common American Universal Product Code UPC and the European EAN coding system 
 note 
 string 
 no 
 Movement note 
 status 
 string 
 no 
 Movement status ( D - draft, N - new, S - wait shipping, R - wait receiving, T - on the way, C - completed) 
 movement_items 
 array 
 yes 
 Array of moved inventory items (information about moveable 
…(qisqartirildi)
```

### Documents › Warehouse › Internal movement › Internal movement / Export
- **POST** `/b/anor/mxsx/mkw/movement$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "movement_id": "",
  "begin_from_movement_date": "",
  "end_from_movement_date": "",
  "begin_to_movement_date": "",
  "end_to_movement_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on interorganizational movements for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "movement_id": "",
 "begin_from_movement_date": "",
 "end_from_movement_date": "",
 "begin_to_movement_date": "",
 "end_to_movement_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "movement": [
 {
 "filial_code": "",
 "external_id": "",
 "movement_id": "",
 "movement_number": "",
 "from_movement_date": "",
 "to_movement_date": "",
 "request_id": "",
 "status": "",
 "from_warehouse_code": "",
 "to_warehouse_code": "",
 "reason_code": "",
 "note": "",
 "barcode": "",
 "movement_items": [
 {
 "external_id": "",
 "movement_item_id": "",
 "request_item_id": "",
 "product_code": "",
 "serial_number": "",
 "inventory_kind": "",
 "on_balance": "",
 "card_code": "",
 "expiry_date": "",
 "quantity": "",
 "batch_number": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Description 
 filial_codes 
 array 
 Array with data of organizations involved in the movement * 
 filial_code 
 string 
 Organization unique code 
 external_id 
 string 
 Movement ID assigned by third party software 
 movement_id 
 number 
 Movement ID assigned by Smartup 
 begin_from_movement_date 
 date(dd.mm.yyyy) 
 Filter by shipping begin date 
 end_from_movement_date 
 date(dd.mm.yyyy) 
 Filter by shipping end date 
 begin_to_movement_date 
 date(dd.mm.yyyy) 
 Filter by receiving begin date 
 end_to_movement_date 
 date(dd.mm.yyyy) 
 Filter by receiving end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 Filter by date of modification 
 end_modified_on 
 date dd.mm.yyyy) 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 movement 
 array 
 Array with data on the interorganizational movement (information about the move itself) 
 filial_code 
 string 
 Organization unique code 
 external_id 
 string 
 Movement ID assigned by third party software 
 movement_id 
 number 
 Movement ID assigned by Smartup 
 request_id 
 number 
 Request ID 
 movement_number 
 string 
 Movement number 
 from_m
…(qisqartirildi)
```

### Documents › Warehouse › Stocktaking › Stocktaking / Import
- **POST** `/b/anor/mxsx/mkw/stocktaking$import`
```json
{
  "stocktaking": [
    {
      "filial_code": "",
      "external_id": "",
      "stocktaking_id": "",
      "stocktaking_number": "001",
      "stocktaking_date": "01.09.2021",
      "status": "D",
      "warehouse_code": "100",
      "currency_code": "860",
      "reason_code": "",
      "note": "Planned stocktaking",
      "stocktaking_items": [
        {
          "external_id": "",
          "stocktaking_item_id": "",
          "product_code": "6201191",
          "serial_number": "",
          "inventory_kind": "G",
          "card_code": "",
          "expiry_date": "",
          "batch_number": "",
          "quantity": "1000",
          "income_price": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
This interface uploads inventory data to the Smartup X from third party software. The interface supports bulk data ingestion in a single request. 
 Request 
 {
 "stocktaking": [
 {
 "filial_code": "",
 "external_id": "",
 "stocktaking_id": "",
 "stocktaking_number": "001",
 "stocktaking_date": "01.09.2021",
 "status": "D",
 "warehouse_code": "100",
 "currency_code": "860",
 "reason_code": "",
 "note": "Planned stocktaking",
 "stocktaking_items": [
 {
 "external_id": "",
 "stocktaking_item_id": "",
 "product_code": "6201191",
 "serial_number": "",
 "inventory_kind": "G",
 "card_code": "",
 "expiry_date": "",
 "batch_number": "",
 "balance_quantity": "",
 "quantity": "1000",
 "income_price": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 stocktaking 
 array 
 yes 
 Array with stocltaking data 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Stocktaking ID assigned by third party software 
 stocktaking_id 
 number 
 no 
 Stocktaking ID assigned by Smartup 
 stocktaking_number 
 string 
 no 
 Stocktaking number 
 stocktaking_date 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Stocktaking date 
 status 
 string 
 no 
 The status of the stocktaking (P - posted, D - draft, C -cancelled) If no status was set, it will be saved as Draft (D) 
 warehouse_code 
 string 
 yes 
 Unique warehouse code 
 reason_code 
 string 
 no 
 Reason for stocktaking. Select a pre-created 
 currency_code 
 string 
 yes 
 Currency code 
 note 
 string 
 no 
 Stocktaking note 
 barcode 
 string 
 no 
 A barcode is coded information applied to packaging in the form of strokes, read using special devices. With the help of a bar code, information about some of the most significant product parameters is encoded. The most common American Universal Product Code UPC and the European EAN coding system 
 stocktaking_items 
 array 
 yes 
 An array with data on the article of goods and materials participating in the stocktaking list 
 external_id 
 string 
 no 
 Invenotory SKU ID assigned by third-party software 
 stocktaking_item_id 
 number 
 no 
 Inventory SKU ID assigned by Smartup 
 product_code 
 string 
 yes 
 Unique merchandise code 
 serial_number 
 string 
 no 
 Serial number 
 inventory_kind 
 string 
 yes 
 Type of goods and materials ( P - products, G - goods, M - raw materials). Type of goods and mate
…(qisqartirildi)
```

### Documents › Warehouse › Stocktaking › Stocktaking / Export
- **POST** `/b/anor/mxsx/mkw/stocktaking$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "stocktaking_id": "",
  "begin_stocktaking_date": "",
  "end_stocktaking_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on inter -organizational movements for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "stocktaking_id": "",
 "begin_stocktaking_date": "",
 "end_stocktaking_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "stocktaking": [
 {
 "filial_code": "",
 "external_id": "",
 "stocktaking_id": "",
 "stocktaking_number": "",
 "stocktaking_date": "",
 "status": "",
 "warehouse_code": "",
 "currency_code": "",
 "reason_code": "",
 "note": "",
 "barcode": "",
 "income_batch_number": "",
 "c_income_amount": "",
 "c_income_amount_base": "",
 "c_expense_amount": "",
 "c_expense_amount_base": "",
 "stocktaking_items": [
 {
 "external_id": "",
 "stocktaking_item_id": "",
 "product_code": "",
 "inventory_kind": "",
 "card_code": "",
 "serial_number": "",
 "expiry_date": "",
 "balance_quantity": "",
 "quantity": "",
 "batch_number": "",
 "income_price": "",
 "income_amount": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_codes 
 array 
 no 
 Array with data of organizations participating in the stocktaking (!) 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Stocktaking ID assigned by third party software 
 stocktaking_id 
 number 
 no 
 Stocktaking ID assigned by Smartup 
 begin_stocktaking_date 
 date(dd.mm.yyyy) 
 no 
 Filter by stocktaking begin date 
 end_stocktaking_date 
 date(dd.mm.yyyy) 
 no 
 Filter by stocktaking end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 ! - the array is used when it is necessary to upload data from two or more organizations. If less than two organizations are involved in the process, the filial _ code parameter is used outside the array. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 stocktaking 
 array 
 Array with inventory data 
 filial_code 
 string 
 Organization unique code 
 external_id 
 string 
 Stocktaking ID assigned by third party software 
…(qisqartirildi)
```

### Documents › Warehouse › Write-off › Write-off / Import
- **POST** `/b/anor/mxsx/mkw/writeoff$import`
```json
{
  "writeoff": [
    {
      "filial_code": "",
      "external_id": "",
      "writeoff_id": "",
      "writeoff_number": "",
      "writeoff_date": "",
      "status": "",
      "warehouse_code": "",
      "reason_code": "",
      "currency_code": "",
      "note": "",
      "writeoff_items": [
        {
          "external_id": "",
          "writeoff_item_id": "",
          "product_code": "",
          "serial_number": "",
          "inventory_kind": "",
          "card_code": "",
          "expiry_date": "",
          "quantity": "",
          "batch_number": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
The functionality of loading write-offs from third-party software. This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "writeoff": [
 {
 "filial_code": "",
 "external_id": "",
 "writeoff_id": "",
 "writeoff_number": "",
 "writeoff_date": "",
 "status": "",
 "warehouse_code": "",
 "reason_code": "",
 "currency_code": "",
 "note": "",
 "writeoff_items": [
 {
 "external_id": "",
 "writeoff_item_id": "",
 "product_code": "",
 "serial_number": "",
 "inventory_kind": "",
 "card_code": "",
 "expiry_date": "",
 "quantity": "",
 "batch_number": "",
 "marking_codes": [
 {
 "marking_code": ""
 }
 ]
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 write off 
 array 
 yes 
 Array with write-off data 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Write-off ID assigned by third party software 
 writeoff_id 
 number 
 no 
 ID assigned by Smartup 
 writeoff_number 
 string 
 no 
 Item write-off number 
 writeoff_date 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Date of write-off of goods and materials from the warehouse 
 warehouse_code 
 string 
 yes 
 The unique code of the warehouse for which the write-off is taking place 
 currency_code 
 string 
 yes 
 The unique code of the write-off currency 
 reason_code 
 string 
 no 
 Reason for write-off. Select a pre-created 
 note 
 string 
 no 
 Write-off note 
 status 
 string 
 no 
 Write-off status. Possible values: D - Draft, A - In Assembly, P - Posted. Note: Status "C - Completed" is not applicable via API. Completion requires a responsible officer to add expenses and their amount in the system. 
 writeoff_items 
 array 
 yes 
 Array with data on the inventory item to be written off 
 external_id 
 string 
 no 
 Identifier of the write-off article assigned by third-party software 
 writeoff_item_id 
 number 
 no 
 ID assigned by Smartup 
 product_code 
 string 
 yes 
 Unique inventory code assigned for integration with third-party software 
 serial_number 
 string 
 no 
 Serial number 
 inventory_kind 
 string 
 yes 
 Type of goods and materials ( P - products, G - goods, M - raw materials). Type of goods and materials specifies the category of ownership 
 quantity 
 number 
 yes 
 Amount of inventory to be written off 
 card_code 
 string 
 no 
 Inventory card number 
 expiry_date 
 string 
 no 
 Expiry date 
…(qisqartirildi)
```

### Documents › Warehouse › Write-off › Write-off / Export
- **POST** `/b/anor/mxsx/mkw/writeoff$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "writeoff_id": "",
  "begin_writeoff_date": "",
  "end_writeoff_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on write-offs for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "writeoff_id": "",
 "begin_writeoff_date": "",
 "end_writeoff_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "writeoff": [
 {
 "filial_code": "",
 "external_id": "",
 "writeoff_id": "",
 "writeoff_number": "",
 "writeoff_date": "",
 "status": "",
 "currency_code": "",
 "barcode": "",
 "warehouse_code": "",
 "reason_code": "",
 "note": "",
 "c_amount": "",
 "c_amount_base": "",
 "writeoff_items": [
 {
 "external_id": "",
 "writeoff_item_id": "",
 "inventory_kind": "",
 "product_code": "",
 "serial_number": "",
 "card_code": "",
 "expiry_date": "",
 "quantity": "",
 "batch_number": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_codes 
 array 
 no 
 Array with data of organizations participating in the write -off (!) 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Write-off ID assigned by third party software 
 writeoff_id 
 number 
 no 
 Write-off ID in the Smartup system 
 begin_writeoff_date 
 date(dd.mm.yyyy) 
 no 
 Filter by write-off begin date 
 end_writeoff_date 
 date(dd.mm.yyyy) 
 no 
 Filter by write-off end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 ! - the array is used when it is necessary to upload the data of two or more organizations. If less than two organizations are involved in the process, the filial _ code parameter is used outside the array. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 write off 
 array 
 Array with write-off data 
 filial_code 
 string 
 Organization unique code 
 external_id 
 string 
 Inventory write-off identifier assigned by third-party software 
 writeoff_id 
 number 
 Inventory write-off ID assigned by Smartup system 
 writeoff_number 
 string 
 Item write-off number 
 writeoff_date 
 date(dd.mm.yyyy) 
 Date of inventory write-off 
 status 
 string 
 Wr
…(qisqartirildi)
```

### Documents › Warehouse › Return to suppliers › Return to suppliers / Import
- **POST** `/b/anor/mxsx/mkw/return$import`
```json
{
  "return": [
    {
      "filial_code": "",
      "external_id": "",
      "return_id": "",
      "return_number": "1",
      "return_time": "02.09.21",
      "status": "D",
      "warehouse_code": "100",
      "reason_code": "",
      "currency_code": "860",
      "supplier_code": "3223",
      "owner_person_code": "",
      "contract_code": "",
      "purchase_id": "",
      "invoice_number": "",
      "invoice_date": "",
      "note": "",
      "return_items": [
        {
          "external_id": "",
          "return_item_id": "",
          "purchase_item_id": "",
          "input_id": "",
          "input_item_id": "",
          "serial_number": "",
          "inventory_kind": "G",
          "on_balance": "",
          "product_code": "",
          "card_code": "",
          "expiry_date": "",
          "quantity": "10",
          "price": "",
          "margin_kind": "",
          "margin_value": "",
          "vat_percent": "",
          "vat_amount": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
This interface uploads supplier returns data to the Smartup X from third party software. The interface supports bulk data ingestion in a single request. 
 Request 
 {
 "return": [
 {
 "filial_code": "",
 "external_id": "",
 "return_id": "",
 "return_number": "1",
 "return_time": "02.09.21",
 "status": "D",
 "warehouse_code": "100",
 "reason_code": "",
 "currency_code": "860",
 "supplier_code": "3223",
 "owner_person_code": "",
 "contract_code": "",
 "purchase_id": "",
 "invoice_number": "",
 "invoice_date": "",
 "note": "",
 "return_items": [
 {
 "external_id": "",
 "return_item_id": "",
 "purchase_item_id": "",
 "input_id": "",
 "input_item_id": "",
 "serial_number": "",
 "inventory_kind": "G",
 "on_balance": "",
 "product_code": "",
 "card_code": "",
 "expiry_date": "",
 "quantity": "10",
 "price": "",
 "margin_kind": "",
 "margin_value": "",
 "vat_percent": "",
 "vat_amount": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 return 
 array 
 yes 
 Array with data on returns to the supplier 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Return ID assigned by third party software 
 return_id 
 number 
 no 
 Return ID in Smartup system 
 return_number 
 string 
 no 
 Return to supplier number 
 return_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Date of return of goods and materials from the warehouse 
 warehouse_code 
 string 
 yes 
 The unique code of the warehouse to which the return is made, set for integration with third-party software 
 currency_code 
 string 
 yes 
 Unique return currency code set for integration with third-party software 
 supplier_code 
 string 
 yes 
 Vendor return code set for integration with third-party software 
 reason_code 
 string 
 no 
 Reason for return. Selected from a pre-created list 
 note 
 string 
 no 
 Return Note 
 owner_person_code 
 string 
 no 
 Owner ID 
 contract_code 
 string 
 no 
 Contract ID in the system 
 purchase_id 
 string 
 no 
 Purchase ID 
 status 
 string 
 no 
 Return to supplier status ( D - draft, N - new, C - completed) 
 invoice_number 
 string 
 no 
 Invoice number 
 invoice_date 
 date(dd.mm.yyyy ) 
 no 
 Invoice date 
 return_items 
 array 
 yes 
 Array with data on the article of goods and materials returned to the supplier 
 external_id 
 string 
 no 
 Return SKU ID assigned by third party softwa
…(qisqartirildi)
```

### Documents › Warehouse › Return to suppliers › Return to suppliers / Export
- **POST** `/b/anor/mxsx/mkw/return$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "return_id": "",
  "begin_return_date": "",
  "end_return_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```

### Documents › Warehouse › Receipts to warehouse › Receipts to warehouse / Import
- **POST** `/b/anor/mxsx/mkw/input$import`
```json
{
  "input": [
    {
      "filial_code": "",
      "external_id": "",
      "input_id": "1",
      "input_number": "",
      "input_time": "02.09.2021",
      "status": "D",
      "warehouse_code": "100",
      "note": "Income to warehouse",
      "input_items": [
        {
          "external_id": "",
          "input_item_id": "1",
          "purchase_id": "545",
          "purchase_item_id": "1",
          "quantity": "1000"
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
The interface allows you to upload data on receipts to the warehouse from third-party software to the Smartup X . This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "input": [
 {
 "filial_code": "",
 "external_id": "",
 "input_id": "1",
 "input_number": "",
 "input_time": "02.09.2021",
 "status": "D",
 "warehouse_code": "100",
 "note": "Income to warehouse",
 "input_items": [
 {
 "external_id": "",
 "input_item_id": "1",
 "purchase_id": "545",
 "purchase_item_id": "1",
 "quantity": "1000",
 "marking_codes": [
 {
 "marking_code": ""
 }
 ]
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 input 
 array 
 yes 
 Array with receipts data 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Identifier of the receipts of inventory items to the warehouse, assigned by third-party software 
 input_id 
 number 
 no 
 Identifier of the receipts of inventory items to the warehouse assigned by Smartup 
 input_number 
 string 
 no 
 Invoice number 
 input_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Date and time of receipts 
 warehouse_code 
 string 
 yes 
 Unique warehouse code 
 note 
 string 
 no 
 Note on the receipts of goods and materials at the warehouse 
 status 
 string 
 no 
 The status of the receipt( D - draft, N - new, C - completed) 
 input_items 
 array 
 yes 
 Array with data on the article of goods and materials in the receipts 
 external_id 
 string 
 no 
 Inventory item ID in the receipt, assigned by third-party software 
 input_item_id 
 number 
 no 
 Inventory item ID in the receipts, assigned by the Smartup system 
 purchase_id 
 number 
 yes 
 Owner ID 
 purchase_item_id 
 number 
 yes 
 Identifier of the article of goods and materials in the purchase 
 quantity 
 number 
 yes 
 Number of goods and materials in the receipts 
 marking_codes 
 array 
 no 
 Array with data of attaching marking codes for product unit 
 marking_code 
 string 
 no 
 Marking code of product 
 Before sending, the service checks the request for: 
 the presence of mandatory parameters 
 parameter validity 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 A
…(qisqartirildi)
```

### Documents › Warehouse › Receipts to warehouse › Receipts to warehouse / Export
- **POST** `/b/anor/mxsx/mkw/input$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "input_id": "",
   "begin_input_date": "",
  "end_input_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on receipts to the warehouse for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "input_id": "",
 "begin_input_date": "",
 "end_input_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": "",
 "producer_codes": [""]
}
 Response 
 {
 "input": [
 {
 "filial_code": "",
 "external_id": "",
 "input_id": "",
 "input_number": "",
 "input_time": "",
 "status": "",
 "warehouse_code": "",
 "note": "",
 "input_items": [
 {
 "external_id": "",
 "input_item_id": "",
 "purchase_id": "",
 "purchase_item_id": "",
 "product_code": "",
 "inventory_kind": "",
 "card_code": "",
 "expiry_date": "",
 "quantity": "",
 "price": "",
 "margin_kind": "",
 "margin_value": "",
 "vat_percent": "",
 "vat_amount": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_codes 
 array 
 no 
 Array with data of organizations participating in the posting of goods and materials (!) 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Identifier of the receipts of inventory items to the warehouse, assigned by third-party software 
 input_id 
 number 
 no 
 ID in the Smartup system 
 begin_input_date 
 date(dd.mm.yyyy hh24:mi:ss) 
 no 
 Filter by receipts begin date 
 end_input_date 
 date(dd.mm.yyyy hh24:mi:ss) 
 no 
 Filter by receipts end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 producer_codes 
 array/string 
 no 
 Filter by Producer code(s) 
 ! - the array is used when it is necessary to upload the data of two or more organizations. If less than two organizations are involved in the process, the filial _ code parameter is used outside the array. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 input 
 array 
 Array with data on receipts at the warehouse 
 filial_code 
 string 
 Organization unique code 
 external_id 
 string 
 Return SKU ID assigned by third party software 
 input_id 
 string 
 Identifier of the receipts of goods and mat
…(qisqartirildi)
```

### Documents › Warehouse › Purchase › Purchase / Import
- **POST** `/b/anor/mxsx/mkw/purchase$import`
```json
{
  "purchase": [
    {
        "filial_code": "",
        "external_id": "",
        "purchase_id": "",
        "purchase_number": "",
        "purchase_time": "",
        "order_id": "",
        "status_code": "",
        "input_date": "",
        "supplier_code": "",
        "contract_code": "",
        "warehouse_code": "",
        "currency_code": "",
        "invoice_number": "",
        "invoice_date": "",
        "total_margin_kind": "",
        "total_margin_value": "",
        "note": "",
        "posted": "",
        "purchase_items": [
          {
            "external_id": "",
            "purchase_item_id": "",
            "product_code": "",
            "order_item_id": "",
            "on_balance": "",
            "serial_number": "",
            "inventory_kind": "",
            "card_code": "",
            "expiry_date": "",
            "quantity": "",
            "price": "",
            "margin_kind": "",
            "margin_value": "",
            "vat_percent": "",
            "vat_amount": ""
          }
        ]
      }
  ]
}
```
**Izoh / sxema:**
```
The service imports purchase data according to the parameter values passed to the service in the request. This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "purchase": [
 {
 "filial_code": "",
 "external_id": "",
 "purchase_id": "",
 "purchase_number": "7",
 "purchase_time": "02.09.2021",
 "order_id": "",
 "status_code": "100",
 "input_date": "02.09.2021",
 "supplier_code": "101",
 "contract_code": "",
 "warehouse_code": "100",
 "currency_code": "860",
 "invoice_number": "1",
 "invoice_date": "02.09.2021",
 "total_margin_kind": "",
 "total_margin_value": "",
 "note": "Receipts to warehouse",
 "posted": "Y",
 "purchase_items": [
 {
 "external_id": "",
 "purchase_item_id": "",
 "product_code": "100",
 "order_item_id": "",
 "on_balance": "",
 "serial_number": "",
 "inventory_kind": "G",
 "card_code": "",
 "expiry_date": "",
 "quantity": "1000",
 "price": "3500",
 "margin_kind": "",
 "margin_value": "",
 "vat_percent": "",
 "vat_amount": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 purchase 
 array 
 yes 
 Purchase data array 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Identifier of the arrival of goods and materials credited to the warehouse, assigned by third-party software 
 purchase_id 
 number 
 no 
 Identifier of the arrival of goods and materials credited to the warehouse, assigned by the Smartup system 
 purchase_number 
 string 
 no 
 Inventory purchase invoice number 
 purchase_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Date and time of purchase 
 input_date 
 date(dd.mm.yyyy hh24:mi:ss) 
 no 
 Date of receiving inventories 
 order_id 
 number 
 no 
 Order ID 
 supplier_code 
 string 
 yes 
 Vendor code 
 warehouse_code 
 string 
 no 
 Unique warehouse code 
 currency_code 
 string 
 yes 
 Unique currency code for the purchase of goods and materials 
 contract_code 
 string 
 no 
 Unique code of the purchase contract for goods and materials 
 invoice_number 
 string 
 no 
 Invoice number 
 invoice_date 
 date(dd.mm.yyyy) 
 no 
 Invoice date 
 total_margin_kind 
 string 
 no 
 Total margin type 
 total_margin_value 
 string 
 no 
 Total margin value 
 note 
 string 
 no 
 Note on the purchase of goods and materials 
 status_code 
 string 
 yes 
 Unique status code 
 posted 
 string 
 yes 
 Completed (Y/N) 
 purchase_items 
…(qisqartirildi)
```

### Documents › Warehouse › Purchase › Purchase / Export
- **POST** `/b/anor/mxsx/mkw/purchase$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "purchase_id": "",
  "begin_purchase_date": "",
  "end_purchase_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
Uploading data on purchases for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "purchase_id": "",
 "begin_purchase_date": "",
 "end_purchase_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "purchase": [
 {
 "filial_code": "",
 "external_id": "",
 "purchase_id": "",
 "purchase_time": "",
 "purchase_number": "",
 "input_date": "",
 "supplier_code": "",
 "invoice_number": "",
 "invoice_date": "",
 "order_id": "",
 "currency_code": "",
 "contract_code": "",
 "total_margin_kind": "",
 "total_margin_value": "",
 "warehouse_code": "",
 "status_code": "",
 "note": "",
 "posted": "",
 "purchase_items": [
 {
 "external_id": "",
 "purchase_item_id": "",
 "product_code": "",
 "inventory_kind": "",
 "order_item_id": "",
 "on_balance": "",
 "serial_number": "",
 "card_code": "",
 "expiry_date": "",
 "base_price": "",
 "quantity": "",
 "price": "",
 "margin_kind": "",
 "margin_value": "",
 "vat_percent": "",
 "vat_amount": "",
 "marking_codes": [
 {
 "marking_code": ""
 }
 ]
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_codes 
 array 
 no 
 Array with data of organizations involved in the procurement process (!) 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Inventory purchase ID assigned by third-party software 
 purchase_id 
 number 
 no 
 Purchase ID in the Smartup system 
 begin_purchase_date 
 date(dd.mm.yyyy) 
 no 
 Filter by purchase begin date 
 end_purchase date 
 date(dd.mm.yyyy) 
 no 
 Filter by purchase end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 ! - the array is used when it is necessary to upload the data of two or more organizations. If less than two organizations are involved in the process, the filial _ code parameter is used outside the array. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 purchase 
 array 
 Purchase data array 
 filial_code 
 string 
 Organization unique code 
 ext
…(qisqartirildi)
```

### Documents › Warehouse › Logistics › Logistics / Import
- **POST** `/b/trade/txs/tdeal/logistics$import`
```json
{
    "logistics": [
        {
            "logistics_id": "",
            "external_id": "",
            "delivery_date": "",
            "expeditor_code": "",
            "van_code": "",
            "lap": "",
            "deals": [
                {
                    "deal_id": ""
                }
            ]
        }
    ]
}
```
**Izoh / sxema:**
```
This method allows you to send and update information about logistics operations, including delivery details, expeditors, vehicles, and associated deals. 
 Request 
 {
 "logistics": [
 {
 "logistics_id": "",
 "external_id": "",
 "delivery_date": "",
 "expeditor_code": "",
 "van_code": "",
 "lap": "",
 "deals": [
 {
 "deal_id": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 logistics 
 array 
 yes 
 An array of objects, each representing a logistics operation 
 logistics_id 
 number 
 no 
 A unique identifier for the logistics operation. This can be empty when creating a new operation 
 external_id 
 string 
 no 
 An external identifier associated with the logistics operation 
 delivery_date 
 date(dd.mm.yyyy) 
 yes 
 The delivery date in the DD.MM.YYYY format 
 expeditor_code 
 string 
 yes 
 A unique code for the expeditor responsible for the delivery 
 van_code 
 string 
 yes 
 The license plate number of the vehicle used for delivery 
 lap 
 string 
 yes 
 The route number for the vehicle within the current logistics chain 
 deals 
 array 
 yes 
 An array of deals associated with this logistics operation 
 deal_id 
 string 
 yes 
 A unique identifier for order in our system 
 Before sending, the service checks the request for: 
 the presence of mandatory parameters 
 parameter validity 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique record code 
 message 
 string 
 Clarifying error messages from the server
```

### Documents › Warehouse › Logistics › Logistics / Export
- **POST** `/b/trade/txs/tdeal/logistics$export`
```json
{
    "logistics": [
        {
            "logistics_id": "",
            "external_id": "",
            "delivery_date": "",
            "expeditor_code": "",
            "expeditor_name": "",
            "van_code": "",
            "van_name": "",
            "lap": "",
            "begin_location": "",
            "end_location": "",
            "cash_register_id": "",
            "cash_register_name": "",
            "deals": [
                {
                    "deal_id": "",
                    "status": "",
                    "external_id": ""
                }
            ]
        }
    ]
}
```
**Izoh / sxema:**
```
This method allows to query logistics operations based on various filtering criteria and retrieve detailed information about each operation. 
 Request 
 {
 "logistics_id": "",
 "external_id": "",
 "delivery_date": "",
 "expeditor_code": "",
 "van_code": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "logistics": [
 {
 "logistics_id": "",
 "external_id": "",
 "delivery_date": "",
 "expeditor_code": "",
 "expeditor_name": "",
 "van_code": "",
 "van_name": "",
 "lap": "",
 "begin_location": "",
 "end_location": "",
 "cash_register_id": "",
 "cash_register_name": "",
 "deals": [
 {
 "deal_id": "",
 "status": "",
 "external_id": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 logistics_id 
 number 
 no 
 A unique identifier for the logistics operation. This can be empty when creating a new operation 
 external_id 
 string 
 no 
 An external identifier associated with the logistics operation 
 delivery_date 
 date(dd.mm.yyyy) 
 no 
 The delivery date in the DD.MM.YYYY format 
 expeditor_code 
 string 
 no 
 A unique code for the expeditor responsible for the delivery 
 van_code 
 string 
 no 
 The license plate number of the vehicle used for delivery 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Before sending, the service checks the request for: 
 the presence of mandatory parameters 
 parameter validity 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 logistics 
 array 
 An array of objects, each representing a logistics operation 
 logistics_id 
 number 
 A unique identifier for the logistics operation. This can be empty when creating a new operation 
 external_id 
 string 
 An external identifier associated with the logistics operation 
 delivery_date 
 date(dd.mm.yyyy) 
 The delivery date in the DD.MM.YYYY format 
 expeditor_code 
 string 
 A unique code for the expeditor responsible for the delivery 
 expeditor_name 
 string 
 The name of the expeditor 
 van_code 
 string 
 The license plate number of the vehicle used for delivery 
 van_name 
 string 
 Th
…(qisqartirildi)
```

### Documents › Warehouse › Logistics › Attach cash register to van
- **POST** `/xtrade/b/trade/txs/tdeal/logistics$attach_cash_register`
```json
{
    "van_id": "",
    "cash_register_id": ""
}
```

### Documents › Finance › Payments from clients › Payments from clients / Import
- **POST** `/b/trade/txs/tcs/cashin$import`
```json
{
  "cashin": [
    {
      "filial_code": "",
      "external_id": "",
      "deal_id": "",
      "cashin_id": "",
      "cashin_time": "",
      "cashin_date": "",
      "cashin_number": "",
      "bill_collector_code": "",
      "client_code": "",
      "subfilial_code": ")",
      "contract_code": "",
      "payment_type_code": "",
      "currency_code": "",
      "cashbox_code": "",
      "bank_account_code": "",
      "amount": "",
      "posted": "",
      "note": "",
      "bank_trans_number": "",
      "bank_trans_date": "",
      "purpose": ""
    }

  ]
}
```
**Izoh / sxema:**
```
The service imports data on payments from clients, in accordance with the values of the parameters passed to the service in the request. This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "cashin": [
 {
 "filial_code": "",
 "external_id": "",
 "deal_id": "",
 "cashin_id": "",
 "cashin_time": "",
 "cashin_date": "",
 "cashin_number": "",
 "bill_collector_code": "",
 "client_code": "",
 "subfilial_code": "",
 "contract_code": "",
 "payment_type_code": "",
 "currency_code": "",
 "cashbox_code": "",
 "bank_account_code": "",
 "amount": "",
 "posted": "",
 "note": "",
 "bank_trans_number": "",
 "bank_trans_date": "",
 "purpose": ""
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 cashin 
 array 
 yes 
 Array with payment data from the client 
 filial_code 
 string 
 no 
 Unique region code 
 external_id 
 string 
 no 
 Identifier of the arrival of goods and materials credited to the warehouse, assigned by third-party software 
 deal_id 
 number 
 no 
 The order ID is automatically assigned by the system 
 cashin_id 
 number 
 no 
 Payment ID assigned by Smartup 
 cashin_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 yes 
 Date and time of receipt of payment from the client 
 cashin_date 
 date(dd.mm.yyyy) 
 yes 
 Date of receipt of payment from the client 
 cashin_number 
 string 
 no 
 Payment document number 
 bill_collector_code 
 string 
 no 
 Collector unique code 
 client_code 
 string 
 yes 
 Unique client code 
 subfilial_code 
 string 
 no 
 Unique project code 
 contract_code 
 string 
 no 
 Unique code of the purchase contract for goods and materials 
 payment_type_code 
 string 
 yes 
 Unique payment type code 
 currency_code 
 string 
 yes 
 Unique currency code for the purchase of goods and materials 
 cashbox_code 
 string 
 yes 
 Unique checkout code 
 bank_account_code 
 string 
 yes 
 Unique current account code 
 amount 
 number 
 yes 
 Sum 
 posted 
 string 
 yes 
 Completed (Y/N) 
 note 
 string 
 no 
 Payment note 
 bank_trans_number 
 number 
 no 
 The number of transfer 
 bank_trans_date 
 date(dd.mm.yyyy) 
 no 
 The date of transfer 
 purpose 
 string 
 no 
 The purpose of transfer 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 

…(qisqartirildi)
```

### Documents › Finance › Payments from clients › Payments from clients / Export
- **POST** `/b/trade/txs/tcs/cashin$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "cashin_id": "",
  "begin_cashin_date": "",
  "end_cashin_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
Through the interface, the service exports data on payments from clients for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "cashin_id": "",
 "begin_cashin_date": "",
 "end_cashin_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "cashin": [
 {
 "filial_code": "",
 "external_id": "",
 "cashin_id": "",
 "cashin_time": "",
 "cashin_date": "",
 "cashin_number": "",
 "bill_collector_code": "",
 "client_code": "",
 "client_id": "",
 "client_name": "",
 "client_tin": "",
 "subfilial_code": "",
 "contract_code": "",
 "payment_type_code": "",
 "currency_code": "",
 "cashbox_code": "",
 "bank_account_code": "",
 "amount": "",
 "posted": "",
 "bank_trans_number": "",
 "bank_trans_date": "",
 "note": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Client payment ID assigned by third party software 
 cashin_id 
 number 
 no 
 Payment ID from the client, in the Smartup system 
 begin_cashin_date 
 date(dd.mm.yyyy) 
 no 
 Filter by payments from clients begin date 
 end_cashin_date 
 date(dd.mm.yyyy) 
 no 
 Filter by payments from clients end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 cashin 
 array 
 Array with payment data from the client 
 filial_code 
 string 
 Unique region code 
 external_id 
 string 
 Identifier of the arrival of goods and materials credited to the warehouse, assigned by third-party software 
 cashin_id 
 number 
 Payment ID assigned by Smartup 
 cashin_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 Date and time of receipt of payment from the client 
 cashin_date 
 date(dd.mm.yyyy) 
 Date of receipt of payment from the client 
 cashin_number 
 string 
 Payment document number 
 bill_collector_code 
 string 
 Collector unique code 
 client_code 
 string 
 Unique client code 
 client_id 
 number 
 Unique client ID 
…(qisqartirildi)
```

### Documents › Finance › Cash Operations › Cash Operations / Import
- **POST** `/b/anor/mxsx/mkcs/cash_operation$import`
```json
{
    "cash_operation": [
        {
            "filial_code": "",
            "external_id": "",
            "operation_id": "",
            "operation_date": "",
            "operation_number": "",
            "subfilial_code": "",
            "posted": "",
            "cashbox_code": "",
            "cashflow_reason_code": "",
            "cashflow_kind": "",
            "corr_coa_code": "",
            "corr_person_code": "",
            "currency_code": "",
            "amount": ""
            "responsible_person_code": ""
            "collector_code": ""
            "note": ""
            "ref_codes": [
                {
                    "ref_type": "",
                    "ref_id": ""
                }
            ]
        }
    ]
}
```
**Izoh / sxema:**
```
The service imports cash operations data according to the parameter values passed to the service in the request. This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "cash_operation": [
 {
 "filial_code": "",
 "external_id": "",
 "operation_id": "",
 "operation_date": "",
 "operation_number": "",
 "subfilial_code": "",
 "posted": "",
 "cashbox_code": "",
 "cashflow_reason_code": "",
 "cashflow_kind": "",
 "corr_coa_code": "",
 "corr_person_code": "",
 "currency_code": "",
 "amount": "",
 "responsible_person_code": "",
 "collector_code": "",
 "note": "",
 "ref_codes": [
 {
 "ref_type": "",
 "ref_id": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data Type 
 Required 
 Description 
 cash_operation 
 array 
 yes 
 Array with data of cash operations 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Cash operation ID assigned by third party software 
 operation_id 
 number 
 no 
 Cash operation ID assigned by Smartup 
 operation_date 
 date(dd.mm.yyyy) 
 yes 
 Cash operation date 
 operation_number 
 string 
 no 
 Cash operation number 
 subfilial_code 
 string 
 no 
 Project code 
 posted 
 string 
 yes 
 Whether cash operation is posted or not (Y - yes, N - no) 
 cashbox_code 
 string 
 yes 
 Cash register code 
 cashflow_reason_code 
 string 
 yes 
 Trasaction type code 
 cashflow_kind 
 string 
 yes 
 Document type 
 corr_coa_code 
 string 
 yes 
 Account code 
 corr_person_code 
 string 
 no 
 Counterparty code 
 currency_code 
 string 
 yes 
 Currency code 
 amount 
 number 
 yes 
 Amount 
 responsible_person_code 
 string 
 no 
 Accountable person code 
 collector_code 
 string 
 no 
 Collector code 
 note 
 string 
 no 
 Note 
 ref_codes 
 array 
 no 
 Array with static data of subcounts. All subcounts mentioned in the "Subcounts" table. 
 ref_type 
 string 
 no 
 Subcount 
 ref_id 
 string 
 no 
 Subcount ID 
 Before sending, the service checks the request for: 
 the presence of mandatory parameters 
 parameter validity 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique record code 
 message 
 string 
 Clarifying e
…(qisqartirildi)
```

### Documents › Finance › Cash Operations › Cash Operations / Export
- **POST** `/b/anor/mxsx/mkcs/cash_operation$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "operation_id": "",
  "begin_operation_date": "",
  "end_operation_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
Through the interface, the service exports data on cash operations for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "operation_id": "",
 "begin_operation_date": "",
 "end_operation_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "cash_operation": [
 {
 "filial_code": "",
 "external_id": "",
 "operation_id": "",
 "operation_date": "",
 "operation_number": "",
 "subfilial_code": "",
 "posted": "",
 "cashbox_code": "",
 "cashflow_reason_code": "",
 "cashflow_kind": "",
 "corr_coa_code": "",
 "corr_person_code": "",
 "currency_code": "",
 "amount": ""
 "responsible_person_code": ""
 "collector_code": ""
 "note": ""
 "ref_codes": [
 {
 "ref_type": "",
 "ref_id": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Cash operation ID assigned by third party software 
 operation_id 
 number 
 no 
 Cash operation ID, in the Smartup system 
 begin_operation_date 
 date(dd.mm.yyyy) 
 no 
 Filter by cash operation begin date 
 end_operation_date 
 date(dd.mm.yyyy) 
 no 
 Filter by cash operation end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data Type 
 Description 
 cash_operation 
 array 
 Array with data of cash operations 
 filial_code 
 string 
 Organization unique code 
 external_id 
 string 
 Cash operation ID assigned by third party software 
 operation_id 
 number 
 Cash operation ID assigned by Smartup 
 operation_date 
 date(dd.mm.yyyy) 
 Cash operation date 
 operation_number 
 string 
 Cash operation number 
 subfilial_code 
 string 
 Project code 
 posted 
 string 
 Whether cash operation is posted or not (Y - yes, N - no) 
 cashbox_code 
 string 
 Cash register code 
 cashflow_reason_code 
 string 
 Trasaction type code 
 cashflow_kind 
 string 
 Document type 
 corr_coa_code 
 string 
 Account code 
 corr_person_code 
 string 
 Co
…(qisqartirildi)
```

### Documents › Finance › Bank Statements › Bank Statements / Import
- **POST** `/b/anor/mxsx/mkcs/bank_operation$import`
```json
{
    "bank_operation" : [
        {
            "filial_code": "",
            "external_id": "",
            "operation_id": "",
            "subfilial_id": "",
            "posted": "",
            "operation_date": "",
            "operation_number": "",
            "bank_trans_number": "",
            "bank_trans_date": "",
            "bank_account_code": "",
            "cashflow_reason_code": "",
            "cashflow_kind": "",
            "corr_coa_code": "",
            "corr_person_code": "",
            "corr_bank_account_code": "",
            "currency_code": "",
            "amount": "",
            "payment_code": "",
            "purpose": "",
            "responsible_person_code" : "",
            "note": "",
            "ref_codes": [
                {
                    "ref_type": "",
                    "ref_id":""
                }
            ]
        }
    ]
}
```
**Izoh / sxema:**
```
StartFragment 
 The interface allows you to upload bank statements data from third-party software to the Smartup. This interface supports bulk data ingestion in a single request 
 EndFragment 
 Request 
 {
 "bank_operation" : [
 {
 "filial_code": "",
 "external_id": "",
 "operation_id": "",
 "subfilial_code": "",
 "posted": "",
 "operation_date": "",
 "operation_number": "",
 "bank_trans_number": "",
 "bank_trans_date": "",
 "bank_account_code": "",
 "cashflow_reason_code": "",
 "cashflow_kind": "",
 "corr_coa_code": "",
 "corr_person_code": "",
 "corr_bank_account_code": "",
 "currency_code": "",
 "amount": "",
 "payment_code": "",
 "purpose": "",
 "responsible_person_code" : "",
 "note": "",
 "ref_codes": [
 {
 "ref_type": "",
 "ref_id":""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 bank_operation 
 array 
 yes 
 Array with data of bank statements 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Bank statement ID assigned by third party software 
 operation_id 
 number 
 no 
 Bank statement ID assigned by Smartup 
 subfilial_code 
 string 
 no 
 Project code 
 posted 
 string 
 yes 
 Whether bank statement is posted or not (Y - yes, N - no) 
 operation_date 
 date(dd.mm.yyyy) 
 yes 
 Bank statement operation date 
 operation_number 
 string 
 no 
 Bank statement operation number 
 bank_trans_number 
 string 
 no 
 Transfer No. 
 bank_trans_date 
 date(dd.mm.yyyy) 
 no 
 Transer Date 
 bank_account_code 
 string 
 yes 
 Currenct account code 
 cashflow_reason_code 
 string 
 yes 
 Trasaction type code 
 cashflow_kind 
 string 
 yes 
 Document type 
 corr_coa_code 
 string 
 yes 
 Account code 
 corr_person_code 
 string 
 no 
 Counterparty code 
 corr_bank_account_code 
 string 
 no 
 Counterparty current account 
 currency_code 
 string 
 yes 
 Currency code 
 amount 
 number 
 yes 
 Amount 
 payment_code 
 string 
 no 
 Payment code 
 purpose 
 string 
 no 
 Payment details 
 responsible_person_code 
 string 
 no 
 Accountable person code 
 note 
 string 
 no 
 Note 
 ref_codes 
 array 
 no 
 Array with data of subcounts 
 ref_type 
 string 
 no 
 Subcount 
 ref_id 
 string 
 no 
 Subcount ID 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique reco
…(qisqartirildi)
```

### Documents › Finance › Bank Statements › Bank Statements / Export
- **POST** `/b/anor/mxsx/mkcs/bank_operation$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "filial_code": "",
  "external_id": "",
  "operation_id": "",
  "begin_operation_date": "",
  "end_operation_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
Through the interface, the service exports data on bank statements for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "filial_code": "",
 "external_id": "",
 "operation_id": "",
 "begin_operation_date": "",
 "end_operation_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "bank_operation" : [
 {
 "filial_code": "",
 "external_id": "",
 "operation_id": "",
 "subfilial_id": "",
 "posted": "",
 "operation_date": "",
 "operation_number": "",
 "bank_trans_number": "",
 "bank_trans_date": "",
 "bank_account_code": "",
 "cashflow_reason_code": "",
 "cashflow_kind": "",
 "corr_coa_code": "",
 "corr_person_code": "",
 "corr_bank_account_code": "",
 "currency_code": "",
 "amount": "",
 "payment_code": "",
 "purpose": "",
 "responsible_person_code" : "",
 "note": "",
 "ref_codes": [
 {
 "ref_type": "",
 "ref_id":""
 }
 ]
 }
 ]
}
 Description pf request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_code 
 string 
 no 
 Organization unique code 
 external_id 
 string 
 no 
 Bank statement ID assigned by third party software 
 operation_id 
 number 
 no 
 Bank statement ID, in the Smartup system 
 begin_operation_date 
 date(dd.mm.yyyy) 
 no 
 Filter by bank statement begin date 
 end_operation_date 
 date(dd.mm.yyyy) 
 no 
 Filter by bank statement end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 bank_operation 
 array 
 Array with data of bank statements 
 filial_code 
 string 
 Organization unique code 
 external_id 
 string 
 Bank statement ID assigned by third party software 
 operation_id 
 number 
 Bank statement ID assigned by Smartup 
 subfilial_code 
 string 
 Project code 
 posted 
 string 
 Whether bank statement is posted or not (Y - yes, N - no) 
 operation_date 
 date(dd.mm.yyyy) 
 Bank statement operation date 
 operation_number 
 string 
 Bank statement operation number 
 bank_trans_number 
 string 
 Transfer No. 
 bank_trans_date 
 date(dd.mm.yyyy) 
 Transer
…(qisqartirildi)
```

### Documents › Equipment › Equipment movement › Movement import
- **POST** `/b/anor/mxsx/mqpf/equipment_movement$import`
```json
{
    "equipment_movement": [
    {
        "filial_code": "",
        "external_id": "",
        "movement_number": "",
        "movement_time": "",
        "from_room_code": "",
        "from_person_code": "",
        "to_room_code": "",
        "to_person_code": "",
        "robot_code": "",
        "warehouse_code": "",
        "status": "",
        "note": "",
        "items": [
            {
            "equipment_code": "",
            "serial_number": ""
            }
        ]
    }
   ]
}
```
**Izoh / sxema:**
```
This interface uploads equipment movement data (transfers between workspaces/persons) to Smartup from third-party software. 
 Request 
 {
 "equipment_movement": [
 {
 "movement_id": "",
 "filial_code": "",
 "external_id": "",
 "movement_number": "",
 "movement_time": "",
 "from_room_code": "",
 "from_person_code": "",
 "to_room_code": "",
 "to_person_code": "",
 "robot_code": "",
 "warehouse_code": "",
 "status": "",
 "note": "",
 "items": [
 {
 "movement_item_id": "",
 "equipment_code": "",
 "serial_number": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of Request Parameters 
 Parameter 
 Data type 
 Description 
 equipment_movement 
 array 
 Array with data on the equipment movement 
 movement_id 
 number 
 Movement ID 
 filial_code 
 string 
 Organization code of searching movement 
 external_id 
 string 
 Movement ID assigned by third party software 
 movement_number 
 string 
 Movement number 
 movement_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 Movement date and time (Date is required) 
 from_room_code 
 string 
 Workspace code (sender) 
 from_person_code 
 string 
 Client's code (sender) 
 to_room_code 
 string 
 Workspace code (recipient) 
 to_person_code 
 string 
 Client's code (recipient) 
 robot_code 
 string 
 Staff Unit code 
 warehouse_code 
 string 
 Warehouse code 
 status 
 string 
 Status of the movement 
 note 
 string 
 Note 
 items 
 array 
 Array with data of movement items 
 movement_item_id 
 number 
 ID of movement inventory 
 equipment_code 
 string 
 Inventory code 
 serial_number 
 string 
 Serial number of inventory 
 Description of Response Parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique code records 
 message 
 string 
 Clarifying error messages from the server
```

### Documents › Equipment › Equipment movement › Movement export
- **POST** `/b/anor/mxsx/mqpf/equipment_movement$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "movement_id": "",
  "external_id": "",
  "begin_movement_date": "",
  "end_movement_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
This interface retrieves equipment movement data from Smartup with filtering capabilities by organization, dates, and statuses. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "movement_id": "",
 "external_id": "",
 "begin_movement_date": "",
 "end_movement_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "equipment_movement": [
 {
 "movement_id": "",
 "filial_code": "",
 "external_id": "",
 "movement_number": "",
 "movement_date": "",
 "movement_time": "",
 "status": "",
 "from_room_code": "",
 "from_room_name": "",
 "to_room_code": "",
 "to_room_name": "",
 "from_person_code": "",
 "from_person_name": "",
 "to_person_code": "",
 "to_person_name": "",
 "robot_code": "",
 "robot_name": "",
 "warehouse_code": "",
 "note": "",
 "items": [
 {
 "movement_item_id": "",
 "equipment_code": "",
 "serial_number": ""
 }
 ]
 }
 ]
}
 Description of Request Parameters 
 Parameter 
 Data type 
 Description 
 filial_codes 
 array 
 Array with data of organizations involved in the movement * 
 filial_code 
 string 
 Organization unique code 
 movement_id 
 number 
 Movement ID assigned by Smartup 
 external_id 
 string 
 Movement ID assigned by third party software 
 begin_movement_date 
 date (dd.mm.yyyy) 
 Filter by movement begin date 
 end_movement_date 
 date (dd.mm.yyyy) 
 Filter by movement end date 
 begin_created_on 
 date(dd.mm.yyyy) 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 Filter by last modified date 
 Description of Response Parameters 
 Parameter 
 Data type 
 Description 
 equipment_movement 
 array 
 Array with data on the equipment movement 
 movement_id 
 number 
 Movement ID assigned by Smartup 
 filial_code 
 string 
 Organization code of searching movement 
 external_id 
 string 
 Movement ID assigned by third party software 
 movement_number 
 string 
 Movement number 
 movement_date 
 date(dd.mm.yyyy) 
 Movement date 
 movement_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 Movement date and time 
 status 
 string 
 Status of the movement 
 from_room_code 
 string 
 Workspace code (sender) 
 from_room_name 
 string 
 Workspace name (sender) 
 to_room_code 
 string 
 Workspace code (recipient) 
 to_room_name 
 string 
 Workspace name(recipient) 
 from_person_code 
 string 
 Client's code (sender) 
 from_person_
…(qisqartirildi)
```

### Documents › Equipment › Equipment movement › Movement change
- **POST** `/b/anor/mxsx/mqpf/equipment_movement$change_status`
```json
{
  "equipment_movement": [
      {
      "movement_id" : "",
      "status": ""
      }
  ]
}
```
**Izoh / sxema:**
```
This interface allows changing the status of equipment movements through the API. 
 Request 
 {
 "equipment_movement": [
 {
 "movement_id" : "",
 "status": ""
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of Request Parameters 
 Parameter 
 Data type 
 Description 
 equipment_movement 
 array 
 Array with data on the equipment movement 
 movement_id 
 number 
 Movement ID assigned by Smartup 
 status 
 string 
 Change previous value to this status 
 Description of Response Parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique code records 
 message 
 string 
 Clarifying error messages from the server
```

### Documents › Equipment › Equipment request › Request import
- **POST** `/b/anor/mxsx/mqpf/equipment_request$import`
```json
{
    "equipment_request": [
    {
        "filial_code": "",
        "external_id": "",
        "request_id": "",
        "request_time": "",
        "request_kind": "",
        "person_code": "",
        "room_code": "",
        "robot_code": "",
        "warehouse_code": "",
        "contract_number": "",
        "contract_begin_date": "",
        "contract_end_date": "",
        "contract_code": "",
        "status": "",
        "note": "",
        "items": [
            {
            "request_item_id": "",
            "equipment_code": "",
            "equipment_group_code": "",
            "equipment_type_code": "",
            "serial_number": ""
            }
        ]
    }
    ]
}
```
**Izoh / sxema:**
```
This interface uploads equipment installation and uninstallation requests to Smartup from third-party software. The interface supports bulk data ingestion in a single request. 
 Request 
 {
 "equipment_request": [
 {
 "filial_code": "",
 "external_id": "",
 "request_id": "",
 "request_time": "",
 "request_kind": "",
 "person_code": "",
 "room_code": "",
 "robot_code": "",
 "warehouse_code": "",
 "contract_number": "",
 "contract_begin_date": "",
 "contract_end_date": "",
 "contract_code": "",
 "status": "",
 "note": "",
 "items": [
 {
 "request_item_id": "",
 "equipment_code": "",
 "equipment_group_code": "",
 "equipment_type_code": "",
 "serial_number": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of Request Parameters 
 Parameter 
 Data type 
 Description 
 equipment_request 
 array 
 Array with data on the equipment requests 
 filial_code 
 string 
 Organization code of searching movement 
 external_id 
 string 
 Request ID assigned by third party software 
 request_id 
 number 
 Request ID 
 request_time 
 date(dd.mm.yyyy hh24:mi:ss) 
 Request date and time (date is required) 
 request_kind 
 string 
 Request type: I - Install, U - Uninstall 
 person_code 
 string 
 Person code (counterparty) 
 room_code 
 string 
 Workspace code 
 robot_code 
 string 
 Staff Unit code 
 warehouse_code 
 string 
 Warehouse code 
 contract_number 
 string 
 Contract number 
 contract_begin_date 
 date(dd.mm.yyyy) 
 Contract start date (required when contract data is needed based on status) 
 contract_end_date 
 date(dd.mm.yyyy) 
 Contract end date (required when contract data is needed based on status) 
 contract_code 
 string 
 Contract code 
 status 
 string 
 Request status 
 note 
 string 
 Note 
 items 
 array 
 Array with data of request items 
 request_item_id 
 number 
 ID of movement inventory in request 
 equipment_code 
 string 
 Inventory code 
 equipment_group_code 
 string 
 Equipment group code 
 equipment_type_code 
 string 
 Equipment type code 
 serial_number 
 string 
 Serial number of inventory 
 Description of Response Parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique code records 
 message 
 string 
 Clarifying error messages from the server
```

### Documents › Equipment › Equipment request › Request export
- **POST** `/b/anor/mxsx/mqpf/equipment_request$export`
```json
{
  "filial_codes": [
    {
      "filial_code": ""
    }
  ],
  "external_id": "",
  "request_id": "",
  "begin_request_date": "",
  "end_request_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
This interface retrieves equipment request data from Smartup X with filtering capabilities by organization, dates, and statuses. 
 Request 
 {
 "filial_codes": [
 {
 "filial_code": ""
 }
 ],
 "external_id": "",
 "request_id": "",
 "begin_request_date": "",
 "end_request_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "equipment_request": [
 {
 "filial_code": "",
 "external_id": "",
 "request_id": "",
 "request_number": "",
 "request_date": "",
 "request_time": "",
 "request_kind": "",
 "person_code": "",
 "person_name": "",
 "room_code": "",
 "room_name": "",
 "robot_code": "",
 "robot_name": "",
 "warehouse_code": "",
 "contract_number": "",
 "contract_begin_date": "",
 "contract_end_date": "",
 "contract_code": "",
 "status": "",
 "note": "",
 "items": [
 {
 "request_item_id": "",
 "equipment_code": "",
 "equipment_group_code": "",
 "equipment_type_code": "",
 "serial_number": ""
 }
 ]
 }
 ]
}
 Description of Request Parameters 
 Parameter 
 Data type 
 Description 
 filial_codes 
 array 
 Array of organization codes for filtering 
 filial_code 
 string 
 Organization code 
 external_id 
 string 
 Request ID assigned by third party software 
 request_id 
 number 
 Request ID assigned by Smartup 
 statuses 
 array 
 Array of status codes for filtering 
 request_kind 
 string 
 Request type filter: I - Install, U - Uninstall 
 begin_request_date 
 date (dd.mm.yyyy) 
 Filter by request begin date 
 end_request_date 
 date (dd.mm.yyyy) 
 Filter by request end date 
 begin_created_on 
 date (dd.mm.yyyy) 
 Filter by creation date 
 end_created_on 
 date (dd.mm.yyyy) 
 Filter by last creation date 
 begin_modified_on 
 date (dd.mm.yyyy) 
 Filter by date of modification 
 end_modified_on 
 date (dd.mm.yyyy) 
 Filter by last modified date 
 Description of Response Parameters 
 Parameter 
 Data type 
 Description 
 equipment_request 
 array 
 Array with equipment request data 
 filial_code 
 string 
 Organization code 
 external_id 
 string 
 Request ID assigned by Smartup 
 request_id 
 number 
 Request ID assigned by third party software 
 request_number 
 string 
 Request number 
 request_date 
 date (dd.mm.yyyy) 
 Request date 
 request_time 
 date(dd.mm.yyyy hh24:mm:ss) 
 Request time 
 request_kind 
 string 
 Request type: I - Install, U - Uninstall 
 person_code 
 string 
 Person code 
 person_name 
 string 
 Person name 
 room_code 
 string 
 Workspace code 
 room_name 
 string 
 
…(qisqartirildi)
```

### Documents › Equipment › Equipment request › Request change
- **POST** `/b/anor/mxsx/mqpf/equipment_request$change_status`
```json
{
  "equipment_request": [
      {
      "request_id" : "",
      "status": ""
      }
  ]
}
```
**Izoh / sxema:**
```
This interface allows changing the status of equipment requests through the API. 
 Request 
 {
 "equipment_request": [
 {
 "request_id" : "",
 "status": ""
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of Request Parameters 
 Parameter 
 Data Type 
 Description 
 equipment_request 
 array 
 Array with data on the equipment requests 
 request_id 
 number 
 Request ID assigned by Smartup 
 status 
 string 
 Change previous value to this status 
 Description of Response Parameters 
 Parameter 
 Data Type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique code records 
 message 
 string 
 Clarifying error messages from the server
```

### References › Inventory › Inventory / Import
- **POST** `/b/anor/mxsx/mr/inventory$import`
- Headers: `project_code: trade`
```json
{
    "inventory": [
        {
            "inventory_id": "",
            "product_id": "",
            "code": "100",
            "name": "Coca-cola 0.5l",
            "short_name": "Coca-cola 0.5l",
            "weight_netto": "0.5",
            "weight_brutto": "0.65",
            "litr": "0.5",
            "box_type_code": "block",
            "box_quant": "12",
            "producer_code": "",
            "measure_code": "kilogram2",
            "state": "A",
            "barcodes": "",
            "order_no": "",
            "article_code": "100",
            "gtin": "",
            "ikpu": "",
            "tnved": "",
            "marking_group_code": "",
            "groups": [
                {
                    "group_code": "Drinks",
                    "type_code": "A"
                }
            ],
            "inventory_kinds": [
                {
                    "inventory_kind": "P"
                }
            ],
            "sector_codes": [
                {
                    "sector_code": "654321"
                }
            ]
        }
    ]
}
```
**Izoh / sxema:**
```
The interface allows you to upload inventory data from third-party software to the Smartup. This interface supports bulk data ingestion in a single request 
 Request 
 {
 "inventory": [
 {
 "inventory_id": "",
 "product_id": "",
 "code": "100",
 "name": "Coca-cola 0.5l",
 "short_name": "Coca-cola 0.5l",
 "weight_netto": "0.5",
 "weight_brutto": "0.65",
 "litr": "0.5",
 "box_type_code": "block",
 "box_quant": "12",
 "producer_code": "",
 "measure_code": "kilogram2",
 "state": "A",
 "barcodes": "",
 "order_no": "",
 "article_code": "100",
 "gtin": "",
 "ikpu": "",
 "tnved": "",
 "marking_group_code": "",
 "groups": [
 {
 "group_code": "Drinks",
 "type_code": "A"
 }
 ],
 "inventory_kinds": [
 {
 "inventory_kind": "P"
 }
 ],
 "sector_codes": [
 {
 "sector_code": "654321"
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": "100"
 }
 ],
 "errors": [
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 inventory 
 array 
 yes 
 Array with data on goods and materials 
 inventory_id 
 number 
 no 
 Unique ID 
 product_id 
 number 
 no 
 Unique ID 
 code 
 string 
 yes 
 Unique inventory code, set for integration with third-party software 
 name 
 string 
 yes 
 Full name of goods and services 
 short_name 
 string 
 no 
 Alternative name of goods and materials 
 box_type_code 
 string 
 no 
 Unique package type code 
 box_quant 
 number 
 no 
 Quantity of goods and materials in the package 
 groups 
 array 
 no 
 Array with data on the characteristics of goods and materials 
 group_code 
 string 
 no 
 Unique code of goods and materials characteristics 
 type_code 
 string 
 no 
 The unique subtype code of the merchandise characteristic 
 measure_code 
 string 
 yes 
 Unique code of the unit of measurement of the service (assigned by the system) 
 state 
 string 
 yes 
 Status (Active / Inactive), where A - active, P - passive 
 barcodes 
 string 
 no 
 Barcode of the inventory 
 producer_code 
 string 
 no 
 Manufacturer's unique code or barcode (graphic information applied to the commodities and materials packaging, which makes it possible to read it by technical means. Several barcodes are separated by a “ 
 weight_brutto 
 number 
 no 
 Weight of goods and materials including packaging 
 weight_netto 
 number 
 no 
 Weight of goods and materials excluding packaging 
 litr 
 number 
 no 
 Volume of goods and materials 
 order_no 
 number 
 no 
 Order number in the list of inventories 
 article_code 
 string 
 no 
 Articl
…(qisqartirildi)
```

### References › Inventory › Inventory / Export
- **POST** `/b/anor/mxsx/mr/inventory$export`
```json
{
  "code": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on inventories for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "code": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "inventory": [
 {
 "product_id": "",
 "code": "",
 "name": "",
 "short_name": "",
 "box_type_code": "",
 "box_quant": "",
 "measure_code": "",
 "producer_code": "",
 "order_no": "",
 "state": "",
 "barcodes":"",
 "weight_netto": "",
 "weight_brutto": "",
 "article_code":"",
 "gtin": "",
 "ikpu": "",
 "tnved": "",
 "litr": "",
 "marking_group_code": "",
 "groups": [
 {
 "group_code": "",
 "type_code": ""
 }
 ],
 "inventory_kinds": [
 {
 "inventory_kind": ""
 }
 ],
 "sector_codes": [
 {
 "sector_code": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 code 
 string 
 No 
 Unique inventory code assigned by the system (allows you to select/filter inventory items by entered code) 
 begin_created_on 
 date( dd.mm.yyyy) 
 No 
 The initial date interval for entering goods and materials into the system (allows you to filter all goods and materials entered into the system after the specified date 
 end_create_on 
 date( dd.mm.yyyy) 
 No 
 The final date interval for entering goods and materials into the system (allows you to filter all goods and materials entered into the system before the specified date 
 begin_modified_on 
 date( dd.mm.yyyy) 
 No 
 Start date interval for editing inventory items in the system (allows you to filter all items changed in the system later than the date set) 
 end_modified_on 
 date( dd.mm.yyyy) 
 No 
 The final date interval for editing goods and materials in the system (allows you to filter all goods and materials changed in the system before the date set 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 inventory 
 array 
 Array with data on goods and materials 
 product_id 
 number 
 Unique ID 
 code 
 string 
 Unique inventory code for integration with third-party software 
 product_id 
 number 
 ID of inventory used within the system 
 name 
 string 
 Complete name of goods and materials 
 short_name 
 string 
 Alternative name of goods and materials 
 weight_netto 
 number 
 Net weight 
 weight_brutto 
 number 
 Gross weight 
 litr 
 number 
 Displacement 
 box_type_code 
 string 
 Unique package type code 

…(qisqartirildi)
```

### References › Service › Service / Import
- **POST** `/b/anor/mxsx/mr/service$import`
```json
{
  "service": [
    {
      "service_id": "",
      "code": "101",
      "name": "Delivery",
      "short_name": "Delivery",
      "measure_code": "unit",
      "state": "A",
      "groups": [
        {
          "group_code": "100",
          "type_code": ""
        }
      ],
      "order_no": ""
    }
  ]
}
```
**Izoh / sxema:**
```
Through this interface, the service loads data about services into the Smartup system x . The interface supports bulk data ingestion in a single request. 
 Request 
 {
 "service": [
 {
 "service_id": "",
 "code": "101",
 "name": "Delivery",
 "short_name": "Delivery",
 "measure_code": "unit",
 "state": "A",
 "groups": [
 {
 "group_code": "100",
 "type_code": ""
 }
 ],
 "order_no": ""
 }
 ]
}
 Response 
 {
 "successes": [
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 service 
 array 
 yes 
 Array with service data 
 code 
 string 
 yes 
 Unique service code assigned for integration with third-party software 
 service_id 
 number 
 no 
 Unique ID 
 name 
 string 
 yes 
 Full service name 
 short_name 
 string 
 no 
 Alternative service name 
 measure_code 
 string 
 yes 
 Unique code of the unit of measure for the service (assigned by the system) 
 state 
 string 
 yes 
 Service status ( A - active, P - passive) 
 groups 
 array 
 no 
 Array with data about the characteristics of the service 
 group_code 
 string 
 no 
 Unique service characteristic code 
 type_code 
 string 
 no 
 Service characteristic subtype unique code 
 order_no 
 number 
 no 
 Order number in the list of services 
 Before sending, the service checks the request for: 
 • the presence of mandatory parameters; • parameter validity. 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique code records 
 message 
 string 
 Clarifying error messages from the server
```

### References › Service › Service / Export
- **POST** `/b/anor/mxsx/mr/service$export`
```json
{
  "code": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data about services for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "code": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "service": [
 {
 "service_id": "",
 "code": "",
 "name": "",
 "short_name": "",
 "measure_code": "",
 "state": "",
 "groups": [
 {
 "group_code": "",
 "type_code": ""
 }
 ],
 "order_no": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 code 
 string 
 no 
 Unique service code assigned by the user in the system (allows you to select/filter the service by the entered code) 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 service 
 array 
 Array with service data 
 service_id 
 number 
 Unique ID 
 code 
 string 
 Unique service code assigned by the user in the system 
 name 
 string 
 Name of service 
 short_name 
 string 
 Alternative service name 
 measure_code 
 string 
 Unique code of the unit of measure for the service (assigned by the system) 
 state 
 string 
 Service status in the system (A - active, P - passive) 
 groups 
 array 
 Array with data about the characteristics of the service 
 group_code 
 string 
 Unique service characteristic code 
 type_code 
 string 
 Service characteristic subtype unique code 
 order_no 
 number 
 Order number in the list of services
```

### References › Product group › Product group / Import
- **POST** `/b/anor/mxsx/mr/product_group$import`
```json
{
  "product_group": [
    {
      "code": "",
      "product_group_id": "",
      "name": "",
      "product_kind": "",
      "state": "",
      "product_group_types": [
        {
          "code": "",
          "name": "",
          "state": "",
          "order_no": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
The interface creates the required number of new product groups, in addition to the default system groups - goods, raw materials, services, for import. 
 Request 
 {
 "product_group": [
 {
 "code": "",
 "product_group_id": "",
 "name": "",
 "product_kind": "",
 "state": "",
 "product_group_types": [
 {
 "code": "",
 "name": "",
 "state": "",
 "order_no": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 product_group 
 array 
 yes 
 Array with product group data 
 code 
 string 
 yes 
 Unique product group code assigned for integration with third-party software 
 product_group_id 
 number 
 no 
 Unique ID 
 name 
 string 
 yes 
 Full name of the product group 
 product_kind 
 string 
 yes 
 Product type 
 state 
 string 
 yes 
 Product group status ( A - active, P - inactive) 
 product_group_types 
 array 
 yes 
 Array with data about product group types 
 code 
 string 
 yes 
 Unique product group type code assigned for integration with third-party software 
 name 
 string 
 yes 
 Full name of the product group type 
 state 
 string 
 yes 
 Product group type status ( A - active, P - passive) 
 order_no 
 number 
 no 
 Order number in the list of product groups 
 Before sending, the service checks the request for: 
 the presence of mandatory parameters 
 parameter validity 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique code records 
 message 
 string 
 Message specifying the cause of the error from the server
```

### References › Product group › Product group / Export
- **POST** `/b/anor/mxsx/mr/product_group$export`
```json
{
  "code": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The interface creates the required number of new product groups, in addition to the default system groups - goods, raw materials, services. Through the interface, the service exports data about the product group. 
 Request 
 {
 "code": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "product_group": [
 {
 "code": "",
 "product_group_id": "",
 "name": "",
 "product_kind": "",
 "state": "",
 "product_group_types": [
 {
 "code": "",
 "name": "",
 "state": "",
 "order_no":""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 code 
 string 
 no 
 Unique product group code assigned by the user in the system (allows you to select/filter the service by the entered code) 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Product group filter by creation date 
 end_create_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last product group creation date 
 begin_modified_on 
 date( dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Required 
 Description 
 product_group 
 array 
 yes 
 Array with product group data 
 code 
 string 
 yes 
 Unique product group code assigned for integration with third-party software 
 product_group_id 
 number 
 no 
 Unique ID 
 name 
 string 
 yes 
 Full name of the product group 
 product_kind 
 string 
 yes 
 Type of products ( I - inventory, S - services) 
 state 
 string 
 yes 
 Product group status ( A - active, P - passive) 
 product_group_types 
 array 
 yes 
 Array with data about product group types 
 code 
 string 
 yes 
 Unique product group type code 
 name 
 string 
 yes 
 Full name of the product group type 
 state 
 string 
 yes 
 Product group type status ( A - active, P - passive) 
 order_no 
 number 
 no 
 Order number in the list of product groups
```

### References › Price type › Price type / Import
- **POST** `/b/anor/api/v2/mkr/price_type$import`
```json
{
  "price_type": [
    {
      "name": "Price for dispatching",
      "code": "777",
      "with_card": "N",
      "short_name": "PfD",
      "price_type_kind": "S",
      "currency_code": "860",
      "state": "A"
    }
  ]
}
```
**Izoh / sxema:**
```
The functionality of loading price types from third-party software is implemented. This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "price_type": [
 {
 "name": "Price for dispatching",
 "code": "777",
 "with_card": "N",
 "short_name": "PfD",
 "price_type_kind": "S",
 "currency_code": "860",
 "state": "A"
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 price_type 
 array 
 yes 
 Array with data on price types 
 code 
 string 
 yes 
 Unique price type code. A certain type of price is implied (action, promo, return, etc.) 
 name 
 string 
 yes 
 Price type name 
 short_name 
 string 
 yes 
 Alternative price type name 
 price_type_kind 
 string 
 yes 
 Price type ( S - sale price, P - purchase price) 
 currency_code 
 string 
 yes 
 Unique currency code for this price type 
 with_card 
 string 
 yes 
 Accounting identifier of the price type by batches (each batch number has its own price value within one inventory) 
 state 
 string 
 yes 
 Price type status in the system (A - active, P - passive) 
 Before sending, the service checks the request for: 
 the presence of mandatory parameters 
 parameter validity 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique record code 
 message 
 string 
 Clarifying error messages from the server
```

### References › Price type › Price type / Export
- **POST** `/b/anor/api/v2/mkr/price_type$export`
```json
{
    "column_list":["code", "name", "short_name", "with_card", "state", "price_type_kind", "currency_code"],
    "limit": "1000",
    "offset": "0"
}
```
**Izoh / sxema:**
```
The service exports data on price types for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "column_list":["code", "name", "short_name", "with_card", "state", "price_type_kind", "currency_code"],
 "limit": "",
 "offset": ""
}
 Response 
 {
 "count": "",
 "data": [
 {
 "code": "",
 "name": "",
 "short_name": "",
 "with_card": "",
 "state": "",
 "price_type_kind": "",
 "currency_code": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 column_list 
 array 
 no 
 An array of column names to be included in the response (e.g., ["code", "name"]). If empty or not provided, all available columns are returned. This reduces data transfer and improves performance. 
 limit 
 number 
 no 
 The maximum number of objects to return in a single response. The server imposes a hard maximum of 1000 objects per request. Values higher than 1000 are automatically capped at 1000. 
 offset 
 number 
 no 
 The starting index from which to return the objects. Used for pagination in combination with limit (e.g., offset: 1000 gets the next batch of objects after the first 1000). Defaults to 0 if not provided 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 count 
 number 
 Total number of price types 
 data 
 array 
 Price type array 
 code 
 string 
 Unique price type code 
 name 
 string 
 Price type name 
 short_name 
 string 
 Alternative price type name 
 with_card 
 string 
 Accounting identifier for the type of prices by batches (each batch number has its own price value within one inventory) 
 state 
 string 
 Price type status in the system (A - active, P - passive) 
 currency_code 
 string 
 Unique currency code 
 price_type_kind 
 string 
 Type of price ( S - sale price, P - purchase price)
```

### References › Inventory price › Inventory price / Import
- **POST** `/b/anor/api/v2/mkf/product_price$import`
```json
{
  "inventory": [
    {
      "inventory_code": "",
      "price_type": [
        {
          "price_type_code": "",
          "card_code": "",
          "price": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
The service loads prices for goods and materials from third-party software. This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "inventory": [
 {
 "inventory_code": "",
 "price_type": [
 {
 "price_type_code": "",
 "card_code": "",
 "price": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 inventory 
 array 
 yes 
 Array with data on goods and materials 
 inventory_code 
 string 
 yes 
 Unique inventory code, set for integration with third-party software 
 price_type_code 
 string 
 yes 
 Unique price type code 
 card_code 
 string 
 no 
 Inventory card number 
 price 
 number 
 yes 
 Price 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique record code 
 message 
 string 
 Clarifying error messages from the server
```

### References › Inventory price › Inventory price / Export
- **POST** `/b/anor/api/v2/mkf/product_price$export`
```json
{
    "price_type_codes":[]
}
```
**Izoh / sxema:**
```
The service exports prices for goods and materials for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "price_type_codes":[""]
}
 Response 
 {
 "inventory": [
 {
 "inventory_code": "",
 "inventory_barcode": "",
 "price_type": [
 {
 "price_type_code": "",
 "card_code": "",
 "price": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 price_type_codes 
 array 
 no ; Exception: if filial_id = administration organization ID, then required 
 An array of price type codes to filter the exported prices. If provided, only prices linked to these types are returned. If empty or not provided, all prices are exported. 
 Description of response parameters 
 Parameter 
 Data type 
 Required 
 Description 
 inventory 
 array 
 yes 
 Array with data on goods and materials 
 inventory_code 
 string 
 yes 
 Unique inventory code, set for integration with third-party software 
 inventory_barcode 
 string 
 yes 
 Unique inventory barcode 
 price_type 
 array 
 yes 
 Array with data of price type for the inventory 
 price_type_code 
 string 
 yes 
 Unique price type code 
 card_code 
 string 
 no 
 Inventory card number 
 price 
 number 
 yes 
 Price
```

### References › Producers › Producers / Import
- **POST** `/b/anor/mxsx/mr/producer$import`
```json
{
  "producer": [
    {
      "person_code": "",
      "state": "",
      "code": "",
      "order_no": ""
    }
  ]
}
```
**Izoh / sxema:**
```
The service imports data about the producer(s) according to the parameter values passed to the service in the request. This interface supports bulk data ingestion in a single request. To implement bulk input, it is necessary to duplicate the producer array in the request with the appropriate parameters the number of times you need. 
 Request 
 {
 "producer": [
 {
 "person_code": "",
 "state": "",
 "code": "",
 "order_no": ""
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 producer 
 array 
 yes 
 An array containing data about the producer 
 person_code 
 string 
 yes 
 Unique face code 
 state 
 string 
 yes 
 Producer status ( A - active; P - passive) 
 code 
 string 
 yes 
 Producer's unique code 
 order_no 
 number 
 no 
 Order number in the list of producers 
 Before sending, the service checks the request for: 
 the presence of mandatory parameters 
 parameter validity 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Producer's unique code used for verification in the system 
 message 
 string 
 Message specifying the cause of the error from the server
```

### References › Producers › Producers / Export
- **POST** `/b/anor/mxsx/mr/producer$export`
```json
{
  "code": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
Uploading data about manufacturers for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. To implement bulk input, it is necessary to duplicate the producer array in the request with the appropriate parameters as many times as you need. 
 Request 
 {
 "code": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "producer": [
 {
 "person_code": "",
 "state": "",
 "order_no": "",
 "code": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 code 
 string 
 no 
 Unique producer's code assigned by the user in the system (allows you to select/filter the service by the entered code) 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Producer filter by creation date 
 end_create_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date of producers 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 producer 
 array 
 Producer data array 
 person_code 
 string 
 Unique face code 
 state 
 string 
 Producer status ( A - active, P - passive) 
 order_no 
 number 
 Order number in the list of producers 
 code 
 string 
 Producer unique code
```

### References › Legal entity › Legal entity / Import
- **POST** `/b/anor/mxsx/mr/legal_person$import`
```json
{
  "legal_person": [
    {
      "name": "OOO Green White Solutions",
      "code": "007",
      "person_id": "",
      "short_name": "GWS",
      "region_code": "Tashkent",
      "is_budgetarian": "Y",
      "tin": "965234875",
      "state": "A",
      "primary_person_code": "",
      "parent_person_code": "",
      "barcode": "48465198",
      "vat_code": "566419465165",
      "cea": "",
      "main_phone": "+9987112030301",
      "email": "info@greenwhite.uz",
      "web": "",
      "address": "Tashkent, Beshagach 1",
      "post_address": "",
      "address_guide": "",
      "zip_code": "32105",
      "latlng": "",
      "is_client": "",
      "is_supplier": "",
      "groups": [
        {
          "group_code": "",
          "type_code": ""
        }
      ],
       "bank_accounts": [
 {
          "bank_account_id": "",
          "bank_account_code": "",
          "bank_account_name": "",
          "is_main": "",
          "currency_code": "",
          "state": "",
          "note": "",
          "mfo": ""
 }
],
 "rooms": [
        {
          "room_code": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
The service imports data about legal entities, in accordance with the values of the parameters passed to the service in the request. This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "legal_person": [
 {
 "name": "OOO Green White Solutions",
 "code": "007",
 "person_id": "",
 "short_name": "GWS",
 "region_code": "Tashkent",
 "is_budgetarian": "Y",
 "tin": "965234875",
 "state": "A",
 "primary_person_code": "",
 "parent_person_code": "",
 "barcode": "48465198",
 "vat_code": "566419465165",
 "cea": "",
 "main_phone": "+9987112030301",
 "email": "info@greenwhite.uz",
 "web": "",
 "address": "Tashkent, Beshagach 1",
 "post_address": "",
 "address_guide": "",
 "zip_code": "32105",
 "latlng": "",
 "is_client": "",
 "is_supplier": "",
 "groups": [
 {
 "group_code": "",
 "type_code": ""
 }
 ],
 "bank_accounts": [
 {
 "bank_account_id": "",
 "bank_account_code": "",
 "bank_account_name": "",
 "is_main": "",
 "currency_code": "",
 "state": "",
 "note": "",
 "mfo": ""
 }
],
 "rooms": [
 {
 "room_code": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 legal_person 
 array 
 yes 
 An array containing data about a legal entity 
 code 
 string 
 yes 
 A unique legal entity code assigned for integration with third-party software 
 person_id 
 number 
 no 
 Unique ID 
 name 
 string 
 yes 
 Full legal name of the legal entity 
 short_name 
 string 
 yes 
 Short alternative name of the legal entity 
 region_code 
 string 
 no 
 Unique code of the region in which the legal entity is located 
 is_budgetarian 
 string 
 yes 
 Whether or not the applicant has a financially responsible person ( Y / N ) 
 tin 
 string 
 yes 
 TIN of a legal entity (taxpayer identification number) 
 state 
 string 
 yes 
 Legal entity status in the system (A - active, P - passive) 
 web 
 string 
 no 
 The website of the legal entity 
 email 
 string 
 no 
 The email of the legal entity 
 primary_person_code 
 string 
 no 
 Code of the counterparty-owner assigned to the legal entity. It is used in case of presence of network points. 
 parent_person_code 
 string 
 no 
 Unique ID of the owner of the legal entity for integration with third-party software. Used when there are network points 
 barcode 
 string 
 no 
 A barcode is coded information applied to packaging in the form of strokes, read using special device
…(qisqartirildi)
```

### References › Legal entity › Legal entity / Export
- **POST** `/b/anor/mxsx/mr/legal_person$export`
```json
{
    "rooms": [
        {
          "room_code": ""
        }
      ],
    "code": "",
    "state": "",
    "begin_created_on": "",
    "end_created_on": "",
    "begin_modified_on": "",
    "end_modified_on": ""
}
```
**Izoh / sxema:**
```
Uploading data on legal entities for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "rooms": [
 {
 "room_code": ""
 }
 ],
 "code": "",
 "filial_code" : "",
 "state": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "legal_person": [
 {
 "person_id": "",
 "name": "",
 "code": "",
 "short_name": "",
 "region_code": "",
 "is_budgetarian": "",
 "tin": "",
 "state": "",
 "primary_person_code": "",
 "parent_person_code": "",
 "barcode": "",
 "vat_code": "",
 "cea": "",
 "main_phone": "+",
 "email": "",
 "web": "",
 "address": "",
 "address_guide": "",
 "zip_code": "",
 "latlng": "",
 "is_client": "",
 "is_supplier": "",
 "groups": [
 {
 "group_code": "",
 "type_code": ""
 }
 ],
 "bank_accounts": [
 {
 "bank_account_id": "",
 "bank_account_code": "",
 "bank_account_name": "",
 "is_main": "",
 "currency_code": "",
 "state": "",
 "note": "",
 "mfo": "",
 "bank_name": ""
 }
],
 "rooms": [
 {
 "room_id": "",
 "room_code": "",
 "room_type_code": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 rooms 
 array 
 no 
 Array with workspaces data 
 room_code 
 string 
 no 
 Workspace code 
 code 
 string 
 no 
 Unique legal entity code assigned by the user in the system (allows you to select/filter the service by the entered code) 
 filial_code 
 string 
 no 
 Organization code; If empty or not provided, information from all available organizations is returned. 
 state 
 string 
 no 
 Filter of legal entitties statuses. There can be 4 options 1. state = "A", filter by all active legal entities 2. state = "P", filter by all inactive legal entities 3. state = "A,P", filter all active and inactive legal entities 4. state = "", filter all active legal entities 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter legal entities by creation date 
 end_create_on 
 date(dd.mm.yyyy) 
 no 
 Filter by the last date of creation of legal entities 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 person_id 
 number 
 Legal entity's ID 
 legal_person 
 array 
 An array containing data about a legal entity 
 code 
 string 
 A unique legal entity code assigned for int
…(qisqartirildi)
```

### References › Natural persons › Natural persons / Import
- **POST** `/b/anor/mxsx/mr/natural_person$import`
```json
{
  "natural_person": [
    {
      "first_name": "Ivan",
      "last_name": "Ivanov",
      "middle_name": "Ivanovich",
      "code": "1001",
      "person_id": "",
      "birthday": "12.12.2000",
      "gender": "M",
      "region_code": "Tashkent",
      "address": "Tashkent city, Chilanzar district, 20",
      "post_address": "",
      "is_budgetarian": "Y",
      "state": "A",
      "legal_person_code": "",
      "web": "",
      "telegram": "",
      "is_client": "",
      "is_supplier": "",
      "groups": [
        {
          "group_code": "",
          "type_code": ""
        }
      ],
      "main_phone": "",
      "email": "",
      "latlng": ""
    }
  ]
}
```
**Izoh / sxema:**
```
Through this interface, the service uploads data about natural persons to the Smartup X from third party software. The interface supports bulk data ingestion in a single request. 
 Request 
 {
 "natural_person": [
 {
 "first_name": "Ivan",
 "last_name": "Ivanov",
 "middle_name": "Ivanovich",
 "code": "1001",
 "person_id": "",
 "birthday": "12.12.2000",
 "gender": "M",
 "region_code": "Tashkent",
 "address": "Tashkent city, Chilanzar district, 20",
 "post_address": "",
 "is_budgetarian": "Y",
 "state": "A",
 "legal_person_code": "",
 "web": "",
 "telegram": "",
 "is_client": "",
 "is_supplier": "",
 "groups": [
 {
 "group_code": "",
 "type_code": ""
 }
 ],
 "main_phone": "",
 "email": "",
 "latlng": ""
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 natural_person 
 array 
 yes 
 Array with data about natural persons 
 first_name 
 string 
 yes 
 Name of the natural person 
 last_name 
 string 
 no 
 Surname of natural person 
 middle_name 
 string 
 no 
 Middle name of an natural person 
 code 
 string 
 yes 
 Unique code of an natural person 
 person_id 
 number 
 no 
 Unique ID 
 birthday 
 date(dd.mm.yyyy) 
 no 
 Date of birth of the natural person. 
 gender 
 string 
 yes 
 Gender of an natural person ( M - male , F - fermale ) 
 region_code 
 string 
 no 
 Unique code of the region of residence of an natural person 
 is_budgetarian 
 string 
 yes 
 Is the natural person liable (Y/N) 
 address 
 string 
 no 
 Place of residence of an natural person by registration 
 post_address 
 string 
 no 
 Place of residence of an natural person 
 state 
 string 
 yes 
 Status of an natural person (A - active, P - passive) 
 legal_person_code 
 string 
 no 
 A unique legal entity code used for integration with third-party software. Used when there are network points 
 web 
 string 
 no 
 The website of an natural person, if any, with all the information about him 
 email 
 string 
 no 
 The email of the legal entity 
 latlng 
 string 
 no 
 Latitude and Longitude 
 main_phone 
 string 
 no 
 The main telephone number of an natural person 
 telegram 
 string 
 no 
 Telegram contact 
 is_client 
 string 
 no 
 An option to save natural person as client (Y - yes, N - no) 
 is_supplier 
 string 
 no 
 An option to save natural person as vendor (Y - yes, N - no) 
 groups 
 array 
 no 
 An array with data on the characteri
…(qisqartirildi)
```

### References › Natural persons › Natural persons / Export
- **POST** `/b/anor/mxsx/mr/natural_person$export`
```json
{
  "rooms": [
        {
          "room_code": ""
        }
      ],
  "code": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on natural persons for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "rooms": [
 {
 "room_code": ""
 }
 ],
 "code": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "natural_person": [
 {
 "person_id":"",
 "first_name": "",
 "last_name": "",
 "middle_name": "",
 "code": "",
 "birthday": "",
 "gender": "",
 "region_name": "",
 "region_code": "",
 "address": "",
 "post_address": "",
 "is_budgetarian": "",
 "state": "",
 "legal_person_code": "",
 "web": "",
 "telegram": "",
 "is_client": "",
 "is_supplier": "",
 "groups": [
 {
 "group_code": "",
 "type_code": ""
 }
 ],
 "rooms": [
 {
 "room_id": "",
 "room_code": "",
 "room_type_code": ""
 }
 ],
 "main_phone": "",
 "email": "",
 "latlng": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 rooms 
 array 
 no 
 Array with workspace data 
 room_code 
 string 
 no 
 Workspace code 
 code 
 string 
 no 
 The unique code of an natural person assigned by the user in the system (allows you to select/filter the service by the entered code) 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter natural persons by date of creation. 
 end_create_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date of natural persons. 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by dates of changes made. 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 natural_person 
 array 
 Array with data about natural persons 
 person_id 
 number 
 Natural person's ID 
 first_name 
 string 
 Name of the natural person 
 last_name 
 string 
 Surname of natural person 
 middle_name 
 string 
 Middle name of an natural person 
 code 
 string 
 Unique code of an natural person 
 birthday 
 date(dd.mm.yyyy) 
 Date of birth of the natural person. 
 gender 
 string 
 Gender of an natural person ( M - male , F - fermale ) 
 region_name 
 string 
 The name of the region of natural person 
 region_code 
 string 
 The code of the region of natural person 
 is_budgetarian 
 string 
 Is the natural person liable (Y/N) 
 address 
 string 
 Place of residence of an natural person by registration 
 post_address 
 string 
 Place of residence of an natural person 
 state 
 string 
 Status o
…(qisqartirildi)
```

### References › Persons group › Persons group / Import
- **POST** `/b/anor/mxsx/mr/person_group$import`
```json
{
  "person_group": [
    {
      "code": "",
      "person_group_id": "",
      "name": "",
      "person_kind": "",
      "state": "",
      "person_group_types": [
        {
          "code": "",
          "name": "",
          "state": "",
          "order_no": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
The interface creates the required number of new groups of persons in addition to the default system groups - legal and natural persons, for import. 
 Request 
 {
 "person_group": [
 {
 "code": "",
 "person_group_id": "",
 "name": "",
 "person_kind": "",
 "state": "",
 "person_group_types": [
 {
 "code": "",
 "name": "",
 "state": "",
 "order_no": ""
 }
 ]
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 person_group 
 array 
 yes 
 Array with data about a group of persons 
 code 
 string 
 yes 
 Unique code of a group of persons, set for integration with third-party software 
 person_group_id 
 number 
 no 
 Unique ID 
 name 
 string 
 yes 
 Full name of the group of persons 
 person_kind 
 string 
 yes 
 Type of person ( N - natural person, L - legal entity) 
 state 
 string 
 yes 
 The status of a group of persons in the system ( A - active, P - passive) 
 person_group_types 
 array 
 no 
 An array with data on the characteristics of a group of persons 
 code 
 string 
 yes 
 Unique code of characteristics of a group of persons 
 name 
 string 
 yes 
 Full name of the person group type 
 state 
 string 
 yes 
 The status of the type of group of persons in the system ( A - active, P - passive) 
 order_no 
 number 
 no 
 Order number in the list of person groups 
 Before sending, the service checks the request for: 
 the presence of mandatory parameters 
 parameter validity 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique code records 
 message 
 string 
 Clarifying error messages from the server
```

### References › Persons group › Persons group / Export
- **POST** `/b/anor/mxsx/mr/person_group$export`
```json
{
  "code": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The interface creates the required number of new groups of persons in addition to the default system groups - legal and natural persons. Through the interface, the service exports data about a group of persons. 
 Request 
 {
 "code": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "person_group": [
 {
 "code": "",
 "person_group_id": "",
 "name": "",
 "person_kind": "",
 "state": "",
 "person_group_types": [
 {
 "code": "",
 "name": "",
 "state": "",
 "order_no":""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 code 
 string 
 no 
 Unique code of a group of persons assigned by the user in the system (allows you to select/filter the service by the entered code) 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 person_group 
 array 
 Array with data about a group of persons 
 code 
 string 
 Unique code of a group of persons, set for integration with third-party software 
 person_group_id 
 number 
 Unique ID 
 name 
 string 
 Full name of the group of persons 
 person_kind 
 string 
 Type of person ( N - natural person, L - legal entity) 
 state 
 string 
 The status of a group of persons in the system (A - active, P - passive) 
 person_group_types 
 array 
 An array with data on the characteristics of a group of persons 
 code 
 string 
 Unique code of characteristics of a group of persons 
 name 
 string 
 Full name of the person group type 
 state 
 string 
 The status of the type of group of persons in the system ( A - active, P - passive) 
 order_no 
 number 
 Order number in the list of person groups
```

### References › Workspaces › Workspaces / Export
- **POST** `/b/anor/mxsx/mrf/room$export`
```json
{
  "code": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on workspaces for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "code": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "room": [
 {
 "room_code": "",
 "room_id":"",
 "filial_code": "",
 "room_name": "",
 "room_type_code": "",
 "state": "",
 "order_no": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 code 
 string 
 no 
 A unique code of workspaces assigned by the user in the system (allows you to select/filter the service by the entered code) 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 room 
 array 
 Array with job data 
 room_code 
 string 
 Unique workspace code set for integration with third-party software 
 room_id 
 number 
 Workspace ID 
 filial_code 
 string 
 Organization code 
 room_name 
 string 
 Worspace name 
 room_type_code 
 string 
 Workspace type 
 state 
 string 
 Workspace status 
 order_no 
 number 
 Order number in the list of workspaces
```

### References › Contract › Contract / Import
- **POST** `/b/anor/mxsx/mkf/contract$import`
```json
{
  "contract": [
    {
      "filial_code": "",
      "external_id": "",
      "contract_id": "",
      "code": "",
      "contract_date": "",
      "contract_number": "",
      "name": "",
      "person_code": "",
      "currency_code": "",
      "expiry_date": "",
      "note": "",
      "initial_amount": "",
      "initial_expiry_date": "",
      "state": "",
      "is_main": "",
      "sub_contracts": [
        {
          "sub_contract_id": "",
          "external_id": "",
          "sub_contract_date": "",
          "sub_contract_number": "",
          "amount": "",
          "expiry_date": ""
        }
      ]
    }
  ]
}
```
**Izoh / sxema:**
```
StartFragment 
 The interface allows you to upload data about contracts from third-party software to the Smartup X . This interface supports bulk data ingestion in a single request 
 Request 
 {
 "contract": [
 {
 "filial_code": "",
 "external_id": "",
 "contract_id": "",
 "code": "",
 "contract_date": "",
 "contract_number": "",
 "name": "",
 "person_code": "",
 "currency_code": "",
 "expiry_date": "",
 "note": "",
 "initial_amount": "",
 "initial_expiry_date": "",
 "state": "",
 "is_main": "",
 "sub_contracts": [
 {
 "sub_contract_id": "",
 "external_id": "",
 "sub_contract_date": "",
 "sub_contract_number": "",
 "amount": "",
 "expiry_date": ""
 }
 ]
 }
 ]
}
 EndFragment 
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_code 
 string 
 yes 
 Organization code 
 external_id 
 string 
 no 
 Contract ID assigned by third party software 
 contract_id 
 number 
 no 
 Contract unique ID 
 code 
 string 
 no 
 Contract code 
 contract_date 
 date(dd.mm.yyyy) 
 yes 
 Contract date 
 contract_number 
 string 
 yes 
 Contract number 
 name 
 string 
 yes 
 The name of contract 
 person_code 
 string 
 yes 
 The person who enters into a contract (it can be natural person or legal entity) 
 currency_code 
 string 
 yes 
 Currency unique code 
 expiry_date 
 date(dd.mm.yyyy) 
 no 
 Contract expiration date 
 note 
 string 
 no 
 Note 
 initial_amount 
 number 
 no 
 The initial amount of money, when first contract was entered 
 initial_expiry_date 
 date 
 no 
 The initial date of expiration, when first contract was entered 
 state 
 string 
 yes 
 Status (Active / Inactive), where A - active, P - passive 
 is_main 
 string 
 no 
 Indicate Main contract. Y - Yes, N - no 
 sub_contracts 
 array 
 Array with data about additional agreements connected to contracts 
 sub_contract_id 
 number 
 no 
 Additional agreement unique ID 
 external_id 
 string 
 no 
 Additional agreement ID assigned by third party software 
 sub_contract_date 
 date(dd.mm.yyyy) 
 yes 
 Additional agreement date 
 sub_contract_number 
 string 
 yes 
 Additional agreement number 
 amount 
 number 
 no 
 The amount of money (last set, if there was change in amount of money) 
 expiry_date 
 date(dd.mm.yyyy) 
 no 
 Expiration date of contract (last set, if there was change in date of expiration) 
 Description of response parameters 
 Parameter 
 Data type
…(qisqartirildi)
```

### References › Contract › Contract / Export
- **POST** `/b/anor/mxsx/mkf/contract$export`
```json
{
  "filial_codes": {
    "filial_code": ""
  },
  "code": "",
  "contract_id": "",
  "begin_contract_date": "",
  "end_contract_date": "",
  "begin_created_on": "",
  "end_created_on": "",
  "begin_modified_on": "",
  "end_modified_on": ""
}
```
**Izoh / sxema:**
```
The service exports data on contracts for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "filial_codes": {
 "filial_code": ""
 },
 "code": "",
 "contract_id": "",
 "begin_contract_date": "",
 "end_contract_date": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "contract": [
 {
 "filial_code": "",
 "contract_id": "",
 "code": "",
 "contract_date": "",
 "contract_number": "",
 "name": "",
 "person_code": "",
 "currency_code": "",
 "expiry_date": "",
 "note": "",
 "initial_amount": "",
 "initial_expiry_date": "",
 "state": "",
 "is_main": "",
 "sub_contracts": [
 {
 "sub_contract_id": "",
 "sub_contract_date": "",
 "sub_contract_number": "",
 "amount": "",
 "expiry_date": ""
 }
 ]
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 filial_codes 
 array 
 no 
 Array with data of contracts 
 filial_code 
 string 
 no 
 Unique filial code 
 code 
 string 
 no 
 Contract code 
 contract_id 
 number 
 no 
 Contract unique ID 
 begin_contract_date 
 date(dd.mm.yyyy) 
 no 
 The beginning date of the period of contract 
 end_contract_date 
 date(dd.mm.yyyy) 
 no 
 The ending date of the period of contract 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter contracts by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 contract 
 array 
 Array with data about contracts 
 code 
 string 
 Contract code 
 filial_code 
 string 
 Organization code 
 contract_id 
 number 
 Contract unique ID 
 contract_date 
 date(dd.mm.yyyy) 
 Contract date 
 contract_number 
 string 
 Contract number 
 name 
 string 
 The name of contract 
 person_code 
 string 
 The person who enters into a contract (it can be natural person or legal entity) 
 currency_code 
 string 
 Unique currency code of contract 
 expiry_date 
 date(dd.mm.yyyy) 
 Contract expiration date 
 note 
 string 
 Note 
 initial_amount 
 number 
 The initial amount of money, when first contract was entered 
 initial_expiry_date 
 date(dd.mm.yyyy) 
 The initial date of expiration, when first contract was entered 
 state 
 string
…(qisqartirildi)
```

### References › Return Reason › Return Reason / Import
- **POST** `/b/anor/mxsx/mdeal/return_reason$import`
```json
{
  "return_reason": [
    {
      "return_reason_id": "",
      "code": "",
      "name": "",
      "state": "",
      "order_no": ""
    }
  ]
}
```
**Izoh / sxema:**
```
The functionality of loading return reasons from third-party software is implemented. This interface supports bulk data ingestion in a single request. 
 Request 
 {
 "return_reason": [
 {
 "return_reason_id": "",
 "code": "",
 "name": "",
 "state": "",
 "order_no": ""
 }
 ]
}
 Response 
 {
 "successes": [
 {
 "code": ""
 }
 ],
 "errors": [
 {
 "code": "",
 "message": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 return_reason 
 array 
 yes 
 Array with data on return reasons 
 return_reason_id 
 number 
 no 
 Unique ID 
 code 
 string 
 yes 
 Return reason code 
 name 
 string 
 yes 
 Retrun reason name 
 state 
 string 
 yes 
 Status (Active / Inactive), where A - active, P - passive 
 order_no 
 number 
 no 
 Order number in the list of return reasons 
 Before sending, the service checks the request for: 
 the presence of mandatory parameters 
 parameter validity 
 If all checks are passed successfully, the service will return the relevant information for each parameter. 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 successes 
 array 
 Array of successfully processed data 
 errors 
 array 
 Array data with errors 
 code 
 string 
 Unique record code 
 message 
 string 
 Clarifying error messages from the server
```

### References › Return Reason › Return Reason / Export
- **POST** `/b/anor/mxsx/mdeal/return_reason$export`
```json
{}
```
**Izoh / sxema:**
```
The service exports data on price types for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "code": "",
 "return_reason_id": "",
 "begin_created_on": "",
 "end_created_on": "",
 "begin_modified_on": "",
 "end_modified_on": ""
}
 Response 
 {
 "return_reason": [
 {
 "return_reason_id": "",
 "code": "",
 "name": "",
 "state": "",
 "order_no": ""
 }
 ]
}
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 code 
 string 
 no 
 Return resaon unique code 
 return_reason_id 
 number 
 no 
 Retrun reason unique ID 
 begin_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter contracts by creation date 
 end_created_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last creation date 
 begin_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by date of modification 
 end_modified_on 
 date(dd.mm.yyyy) 
 no 
 Filter by last modified date 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 return_reason 
 array 
 Return reasons array 
 return_reason_id 
 number 
 Unique return reason ID 
 code 
 string 
 Unique retrun reason code 
 short_name 
 string 
 Retrun reason name 
 state 
 string 
 Status (Active / Inactive), where A - active, P - passive 
 order_no 
 number 
 Order number in the list of return reasons
```

### Others › Inventory Balance / Export
- **POST** `/b/anor/mxsx/mkw/balance$export`
```json
{   
    "warehouse_codes": [
       {
           "warehouse_code": ""
       }
   ],
   "filial_code": "",
   "begin_date": "15.02.2023",
   "end_date": "15.03.2023"
}
```
**Izoh / sxema:**
```
The service exports data on balance of inventories for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 { "warehouse_codes": [
 {
 "warehouse_code": ""
 }
 ],
 "filial_code": "",
 "product_conditions": :["T", "B", "F"],
 "begin_date": "15.02.2023",
 "end_date": "15.03.2023",
 "producer_codes": [ {"supp1", "supp_2" } ]
}
 Response 
 {
 "balance": [
 {
 "date": "16.02.2023",
 "warehouse_id": "61",
 "warehouse_code": "001wrh",
 "product_code": "002pr",
 "product_id": "21",
 "card_code": "",
 "expiry_date": "",
 "serial_number": "",
 "batch_number": "",
 "inventory_kind": "G", //G, M, P
 "quantity": "1400",
 "input_price": "14000",
 "measure_code": "",
 "groups": [
 {
 "group_code": "PRDGR:3",
 "type_code": "102387"
 }
 ],
 "producer_code": "",
 "currency_code": "",
 "base_price": ""
 }
 ]
 }
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 warehouse_codes 
 array 
 no 
 Array with data of warehouses, which balances are related to 
 warehouse_code 
 string 
 no 
 Warehouse code 
 product_conditions 
 array 
 no 
 Array for filtering balances by conditions of inventory. Accepts values "F"(free), "B"(booked), "T"(tranzit). 
 filial_code 
 string 
 no 
 Organization unique code 
 begin_date 
 date(dd.mm.yyyy) 
 yes 
 Filter by inventory balance begin date 
 end_date 
 date(dd.mm.yyyy) 
 yes 
 Filter by inventory balance end date 
 producer_codes 
 array 
 no 
 Filter by Producer code(s) 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 balance 
 array 
 Array with inventory balance data 
 date 
 date(dd.mm.yyyy) 
 The date of inventory balance. (Date works with one-day principle) 
 warehouse_id 
 number 
 Warehouse ID 
 warehouse_code 
 string 
 Warehouse code 
 product_code 
 string 
 Inventory code 
 product_id 
 number 
 Inventory ID 
 card_code 
 string 
 Card code of inventory. In case there are the same 2 card codes of inventories found, system will count as 1. 
 expiry_date 
 date(dd.mm.yyyy) 
 Expiry date of inventory. In case there are the same 2 expiry dates of inventories found, system will count as 1 
 serial_number 
 string 
 Serial number 
 batch_number 
 string 
 Batch number 
 inventory_kind 
 string 
 Type of goods and materials ( P - products, G - goods, M - raw materials). Type of goods and materials specifies the category of ownership 
 quantity 
 number 

…(qisqartirildi)
```

### Others › Equipment Balance / Export
- **POST** `/b/trade/txs/tvt/equipment_balance$export_data`
- Headers: `filial_id: 86401`, `project_code: trade`
```json
{
   "offset": "",
   "limit": "",
   "filial_code": "",
   "room_codes": [
      {
         "room_code": ""
      }
   ],
   "product_type_codes": [
      {
         "product_type_code": ""
      }
   ],
   "product_codes": [
      {
         "product_code": ""
      }
   ]
}
```
**Izoh / sxema:**
```
The service exports data on balance of equipment for a certain period in accordance with the values of the parameters passed to the service in the request. This interface supports bulk sending of data in one request. 
 Request 
 {
 "offset": "",
 "limit": "",
 "filial_code": "",
 "room_codes": [
 {
 "room_code": ""
 }
 ],
 "product_group_codes": [
 {
 "product_group_code": ""
 }
 ],
 "product_type_codes": [
 {
 "product_type_code": ""
 }
 ],
 "product_codes": [
 {
 "product_code": ""
 }
 ]
}
 Response 
 {
 "count": "0",
 "data": [
 {
 "filial_name": "Namangan",
 "installed_date": "08.12.2021",
 "equipment_name": "kuzov",
 "equipment_group_name": null,
 "serial_number": "R734634",
 "equipment_status": "Передано клиенту",
 "warehouse_name": null,
 "contract_name": null,
 "person_id": "187",
 "person_code": null,
 "person_name": "Green White Solutions MCHJ",
 "person_address": "УЛ.Ю.АГЗАМОВА",
 "person_region_name": "Наманганская область",
 "room_name": null,
 "person_current_room_names": "Namangan Lola",
 "supervisor_robot_name": "",
 "agent_name": null,
 "installed_by": "Aziz",
 "last_visit_date": "30.05.2023",
 "equipment's_photo": "Нет",
 "last_inventory_date": null,
 "last_inventory_user_name": null,
 "has_barcode": "Нет",
 "equipment_note": null,
 "lat_lng": null
 }
 ]
 }
 Description of request parameters 
 Parameter 
 Data type 
 Required 
 Description 
 offset 
 number 
 no 
 number of offset 
 limit 
 number 
 no 
 limit of Items max 50 
 filial_code 
 string 
 no 
 Organization unique code 
 room_codes 
 array 
 no 
 Array with workspaces 
 room_code 
 string 
 no 
 Filter by workspace code 
 product_group_codes 
 array 
 no 
 Array with product group codes 
 product_group_code 
 string 
 no 
 Filter by product group code 
 product_type_codes 
 array 
 no 
 Array with product type codes 
 product_type_code 
 string 
 no 
 Filter by product type code 
 product_codes 
 array 
 no 
 Array with products 
 product_code 
 string 
 no 
 Filter by produt code 
 Description of response parameters 
 Parameter 
 Data type 
 Description 
 count 
 number 
 Total number of records 
 data 
 array 
 Array of detailed equipment and personnel data 
 filial_name 
 string 
 Name of the filial 
 installed_date 
 date(dd.mm.yyyy) 
 Date the equipment was installed (dd.mm.yyyy) 
 equipment_name 
 string 
 Name of the equipment 
 equipment_group_name 
 string 
 Group or category to which the equipment belongs 
 serial_number 
 string 
 Unique serial number of the equipmen
…(qisqartirildi)
```