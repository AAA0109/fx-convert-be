from main.apps.settlement.models import Beneficiary

CORPAY_PAYMENT_SETTLEMENT_METHOD_VALUE_MAPPING = {
    Beneficiary.PaymentSettlementMethod.SWIFT: 'W',
    Beneficiary.PaymentSettlementMethod.LOCAL: 'E',
}

CORPAY_CLASSIFICATION_VALUE_MAPPING = {
    Beneficiary.Classification.INDIVIDUAL.value: "Individual",
    Beneficiary.Classification.BUSINESS.value: "Business",
    Beneficiary.Classification.AEROSPACE_DEFENSE.value: "Aerospace and defense",
    Beneficiary.Classification.AGRICULTURE_AGRIFOOD.value: "Agriculture and agric-food",
    Beneficiary.Classification.APPAREL_CLOTHING.value: "Apparel / Clothing",
    Beneficiary.Classification.AUTOMOTIVE_TRUCKING.value: "Automotive / Trucking",
    Beneficiary.Classification.BOOKS_MAGAZINES.value: "Books / Magazines",
    Beneficiary.Classification.BROADCASTING.value: "Broadcasting",
    Beneficiary.Classification.BUILDING_PRODUCTS.value: "Building products",
    Beneficiary.Classification.CHEMICALS.value: "Chemicals",
    Beneficiary.Classification.DAIRY.value: "Dairy",
    Beneficiary.Classification.E_BUSINESS.value: "E-business",
    Beneficiary.Classification.EDUCATIONAL_INSTITUTES.value: "Educational Institutes",
    Beneficiary.Classification.ENVIRONMENT.value: "Environment",
    Beneficiary.Classification.EXPLOSIVES.value: "Explosives",
    Beneficiary.Classification.FISHERIES_OCEANS.value: "Fisheries and oceans",
    Beneficiary.Classification.FOOD_BEVERAGE_DISTRIBUTION.value: "Food / Beverage distribution",
    Beneficiary.Classification.FOOTWEAR.value: "Footwear",
    Beneficiary.Classification.FOREST_INDUSTRIES.value: "Forest industries",
    Beneficiary.Classification.FURNITURE.value: "Furniture",
    Beneficiary.Classification.GIFTWARE_CRAFTS.value: "Giftware and crafts",
    Beneficiary.Classification.HORTICULTURE.value: "Horticulture",
    Beneficiary.Classification.HYDROELECTRIC_ENERGY.value: "Hydroelectric energy",
    Beneficiary.Classification.ICT.value: "Information and communication technologies",
    Beneficiary.Classification.INTELLIGENT_SYSTEMS.value: "Intelligent systems",
    Beneficiary.Classification.LIVESTOCK.value: "Livestock",
    Beneficiary.Classification.MEDICAL_DEVICES.value: "Medical devices",
    Beneficiary.Classification.MEDICAL_TREATMENT.value: "Medical treatment",
    Beneficiary.Classification.MINERALS_METALS_MINING.value: "Minerals, metals and mining",
    Beneficiary.Classification.OIL_GAS.value: "Oil and gas",
    Beneficiary.Classification.PHARMACEUTICALS_BIOPHARMACEUTICALS.value: "Pharmaceuticals and biopharmaceuticals",
    Beneficiary.Classification.PLASTICS.value: "Plastics",
    Beneficiary.Classification.POULTRY_EGGS.value: "Poultry and eggs",
    Beneficiary.Classification.PRINTING_PUBLISHING.value: "Printing /Publishing",
    Beneficiary.Classification.PRODUCT_DESIGN_DEVELOPMENT.value: "Product design and development",
    Beneficiary.Classification.RAILWAY.value: "Railway",
    Beneficiary.Classification.RETAIL.value: "Retail",
    Beneficiary.Classification.SHIPPING_INDUSTRIAL_MARINE.value: "Shipping and industrial marine",
    Beneficiary.Classification.SOIL.value: "Soil",
    Beneficiary.Classification.SOUND_RECORDING.value: "Sound recording",
    Beneficiary.Classification.SPORTING_GOODS.value: "Sporting goods",
    Beneficiary.Classification.TELECOMMUNICATIONS_EQUIPMENT.value: "Telecommunications equipment",
    Beneficiary.Classification.TELEVISION.value: "Television",
    Beneficiary.Classification.TEXTILES.value: "Textiles",
    Beneficiary.Classification.TOURISM.value: "Tourism",
    Beneficiary.Classification.TRADEMARKS_LAW.value: "Trademarks / Law",
    Beneficiary.Classification.WATER_SUPPLY.value: "Water supply",
    Beneficiary.Classification.WHOLESALE.value: "Wholesale"
}

CORPAY_REGULATORY_BENEFICIARY_ACOOUNT_TYPE = {
    Beneficiary.RegulatoryBeneficiaryAccountType.CCAC.value: "CCAC",
    Beneficiary.RegulatoryBeneficiaryAccountType.SVGS.value: "SVGS"
}

CORPAY_BENEFICIARY_VALUE_MAPPING = {
    "payment_methods": CORPAY_PAYMENT_SETTLEMENT_METHOD_VALUE_MAPPING,
    "settlement_methods": CORPAY_PAYMENT_SETTLEMENT_METHOD_VALUE_MAPPING,
    'preferred_method': CORPAY_PAYMENT_SETTLEMENT_METHOD_VALUE_MAPPING,
    "classification": CORPAY_CLASSIFICATION_VALUE_MAPPING,
    "regulatory": CORPAY_REGULATORY_BENEFICIARY_ACOOUNT_TYPE
}

NIUM_PAYMENT_SETTLEMENT_METHOD_VALUE_MAPPING = {
    Beneficiary.PaymentSettlementMethod.LOCAL: 'LOCAL',
    Beneficiary.PaymentSettlementMethod.SWIFT: 'SWIFT',
    Beneficiary.PaymentSettlementMethod.WALLET: 'WALLET',
    Beneficiary.PaymentSettlementMethod.CARD: 'CARD',
    Beneficiary.PaymentSettlementMethod.PROXY: 'PROXY'
}
NIUM_BENEFICIARY_BANK_ACCOUNT_TYPE_VALUE_MAPPING = {
    Beneficiary.BankAccountType.CURRENT: 'Current',
    Beneficiary.BankAccountType.SAVING: 'Saving',
    Beneficiary.BankAccountType.MAESTRA: 'Maestra',
    Beneficiary.BankAccountType.CHECKING: 'Checking'
}
NIUM_PROXY_TYPE_VALUE_MAPPING = {
    Beneficiary.ProxyType.MOBILE: 'MOBILE',
    Beneficiary.ProxyType.UEN: 'UEN',
    Beneficiary.ProxyType.NRIC: 'NRIC',
    Beneficiary.ProxyType.VPA: 'VPA',
    Beneficiary.ProxyType.ID: 'ID',
    Beneficiary.ProxyType.EMAIL: 'EMAIL',
    Beneficiary.ProxyType.RANDOM_KEY: 'RANDOM_KEY',
    Beneficiary.ProxyType.ABN: 'ABN',
    Beneficiary.ProxyType.ORGANISATION_ID: 'ORGANISATION_ID',
    Beneficiary.ProxyType.PASSPORT: 'PASSPORT',
    Beneficiary.ProxyType.CORPORATE_REGISTRATION_NUMBER: 'CORPORATE_REGISTRATION_NUMBER',
    Beneficiary.ProxyType.ARMY_ID: 'ARMY_ID'
}
NIUM_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING = {
    Beneficiary.BankRoutingCodeType.SWIFT: 'SWIFT',
    Beneficiary.BankRoutingCodeType.IFSC: 'IFSC',
    Beneficiary.BankRoutingCodeType.SORT_CODE: 'SORT_CODE',
    Beneficiary.BankRoutingCodeType.ACH_CODE: 'ACH CODE',
    Beneficiary.BankRoutingCodeType.BRANCH_CODE: 'BRANCH CODE',
    Beneficiary.BankRoutingCodeType.BSB_CODE: 'BSB CODE',
    Beneficiary.BankRoutingCodeType.BANK_CODE: 'BANK CODE',
    Beneficiary.BankRoutingCodeType.ABA_CODE: 'ABA_CODE',
    Beneficiary.BankRoutingCodeType.TRANSIT_CODE: 'TRANSIT CODE',
    Beneficiary.BankRoutingCodeType.GENERIC: 'GENERIC',
    Beneficiary.BankRoutingCodeType.WALLET: 'WALLET',
    Beneficiary.BankRoutingCodeType.LOCATION_ID: 'LOCATION ID',
    Beneficiary.BankRoutingCodeType.BRANCH_NAME: 'BRANCH NAME',
    Beneficiary.BankRoutingCodeType.CNAPS: 'CNAPS',
    Beneficiary.BankRoutingCodeType.FEDWIRE: 'FEDWIRE',
    Beneficiary.BankRoutingCodeType.INTERAC: 'INTERAC',
    Beneficiary.BankRoutingCodeType.CHECK: 'CHECK',
}
NIUM_IDENTIFICATION_TYPE_VALUE_MAPPING = {
    Beneficiary.IdentificationType.PASSPORT: 'PASSPORT',
    Beneficiary.IdentificationType.NATIONAL_ID: 'NATIONAL_ID',
    Beneficiary.IdentificationType.DRIVING_LICENSE: 'DRIVING_LICENSE',
    Beneficiary.IdentificationType.OTHERS: 'OTHERS',
    Beneficiary.IdentificationType.CPF: 'CPF',
    Beneficiary.IdentificationType.CNPJ: 'CNPJ'
}
NIUM_BENEFICIARY_ACCOUNT_TYPE_VALUE_MAPPING = {
    Beneficiary.AccountType.INDIVIDUAL: 'Individual',
    Beneficiary.AccountType.CORPORATE: 'Corporate'
}
NIUM_BENEFICIARY_VALUE_MAPPING = {
    "payment_methods": NIUM_PAYMENT_SETTLEMENT_METHOD_VALUE_MAPPING,
    "settlement_methods": NIUM_PAYMENT_SETTLEMENT_METHOD_VALUE_MAPPING,
    'preferred_method': NIUM_PAYMENT_SETTLEMENT_METHOD_VALUE_MAPPING,
    "bank_account_type": NIUM_BENEFICIARY_BANK_ACCOUNT_TYPE_VALUE_MAPPING,
    "proxy_type": NIUM_PROXY_TYPE_VALUE_MAPPING,
    "bank_routing_code_type_1": NIUM_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING,
    "bank_routing_code_type_2": NIUM_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING,
    "inter_bank_routing_code_type_1": NIUM_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING,
    "inter_bank_routing_code_type_2": NIUM_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING,
    "identification_type": NIUM_IDENTIFICATION_TYPE_VALUE_MAPPING,
    "beneficiary_account_type": NIUM_BENEFICIARY_ACCOUNT_TYPE_VALUE_MAPPING
}
MONEX_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING = {
    Beneficiary.BankRoutingCodeType.BSB_CODE: 'bsb',
    Beneficiary.BankRoutingCodeType.ABA_CODE: 'aba',
    Beneficiary.BankRoutingCodeType.SORT_CODE: 'sortCode',
    Beneficiary.BankRoutingCodeType.TRANSIT_CODE: 'transitCode',
    Beneficiary.BankRoutingCodeType.GENERIC: 'generic'
}
MONEX_BANK_ACCOUNT_NUMBER_TYPE_VALUE_MAPPING = {
    Beneficiary.BankAccountNumberType.ACCOUNT_NUMBER: 'accountNumber'
}
MONEX_BENEFICIARY_VALUE_MAPPING = {
    "bank_routing_code_type_1": MONEX_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING,
    "bank_account_number_type": MONEX_BANK_ACCOUNT_NUMBER_TYPE_VALUE_MAPPING,
    "inter_bank_routing_code_1_type": MONEX_BANK_ROUTING_CODE_TYPE_VALUE_MAPPING,
    "inter_bank_account_number_type": MONEX_BANK_ACCOUNT_NUMBER_TYPE_VALUE_MAPPING,
}
