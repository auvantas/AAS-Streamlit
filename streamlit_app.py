import streamlit as st
import stripe
import random
from datetime import datetime, timedelta
import requests
import json

# Initialize Stripe client
if "stripe" not in st.secrets:
    st.error("Stripe API keys are not set in Streamlit secrets.")
    st.markdown("""
    To set up Stripe API keys, add the following to your secrets:
    ```toml
    [stripe]
    api_key = "your_stripe_api_key"
    ```
    For local development:
    1. Create a `.streamlit/secrets.toml` file in your project root with the above content.
    For Streamlit Cloud deployment:
    1. Go to your app's settings in the Streamlit Cloud dashboard.
    2. Find the "Secrets" section and add the above content.
    More info: https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management
    """)
    st.stop()

# Initialize Stripe and Wise API keys
stripe.api_key = st.secrets.stripe.api_key
WISE_API_KEY = st.secrets.wise.api_key
WISE_API_URL = "https://api.transferwise.com"
WISE_PROFILE_ID = st.secrets.wise.profile_id

CURRENCIES = {
    "BGN": "Bulgarian Lev - Bulgaria",
    "CAD": "Canadian Dollar - Canada",
    "CHF": "Swiss Franc - Switzerland and Liechtenstein",
    "CNY": "Chinese Yuan - China",
    "CZK": "Czech Koruna - Czech Republic",
    "DKK": "Danish Krone - Denmark",
    "EUR": "Euro - Multiple European countries",
    "GBP": "British Pound - United Kingdom",
    "HKD": "Hong Kong Dollar - Hong Kong",
    "HUF": "Hungarian Forint - Hungary",
    "ILS": "Israeli Shekel - Israel",
    "NOK": "Norwegian Krone - Norway",
    "NZD": "New Zealand Dollar - New Zealand",
    "PLN": "Polish Zloty - Poland",
    "RON": "Romanian Leu - Romania",
    "SEK": "Swedish Krona - Sweden",
    "SGD": "Singapore Dollar - Singapore",
    "TRY": "Turkish Lira - Turkey",
    "UGX": "Ugandan Shilling - Uganda",
    "USD": "United States Dollar - United States",
    "ZAR": "South African Rand - South Africa"
}

BANK_TRANSFER_REQUIREMENTS = {
    "USD": ["Account Number", "Routing Number (ABA)", "Account Type"],
    "EUR": ["IBAN", "BIC/SWIFT"],
    "GBP": ["Sort Code", "Account Number"],
    "CAD": ["Transit Number", "Institution Number", "Account Number"],
    "AUD": ["BSB Code", "Account Number"],
    "SGD": ["Bank Code", "Branch Code", "Account Number"],
    "HKD": ["Bank Code", "Branch Code", "Account Number"],
    "CNY": ["Bank Name", "Branch Name", "Account Number"],
    "BGN": ["IBAN", "BIC/SWIFT"],
    "CHF": ["IBAN", "BIC/SWIFT"],
    "CZK": ["IBAN", "BIC/SWIFT"],
    "DKK": ["IBAN", "BIC/SWIFT"],
    "HUF": ["IBAN", "BIC/SWIFT"],
    "ILS": ["IBAN", "BIC/SWIFT"],
    "NOK": ["IBAN", "BIC/SWIFT"],
    "NZD": ["Bank Code", "Account Number"],
    "PLN": ["IBAN", "BIC/SWIFT"],
    "RON": ["IBAN", "BIC/SWIFT"],
    "SEK": ["IBAN", "BIC/SWIFT"],
    "TRY": ["IBAN", "BIC/SWIFT"],
    "UGX": ["Bank Name", "Branch Name", "Account Number"],
    "ZAR": ["Branch Code", "Account Number"],
}

BANK_ACCOUNT_DETAILS = {
    "AED": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "AUD": {
        "Account number": "208236946",
        "BSB code": "774-001",
        "Swift/BIC": "TRWIAUS1XXX"
    },
    "BGN": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "CAD": {
        "Account number": "200110754005",
        "Institution number": "621",
        "Transit number": "16001",
        "Swift/BIC": "TRWICAW1XXX"
    },
    "CHF": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "CNY": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "CZK": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "DDK": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "EUR": {
        "IBAN": "BE60 9677 1622 9370",
        "Swift/BIC": "TRWIBEB1XXX"
    },
    "GBP": {
        "Account number": "72600980",
        "UK sort code": "23-14-70",
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "HKD": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "HUF": {
        "Account number": "12600016-16459316-39343647",
        "IBAN": "HU74 1260 0016 1645 9316 3934 3647",
        "Swift/BIC": "TRWIBEBBXXX"
    },
    "ILS": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "NOK": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "NZD": {
        "Account number": "04-2021-0152352-80",
        "Swift/BIC": "TRWINZ21XXX"
    },
    "PLN": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "RON": {
        "Account number": "RO25 BREL 0005 6019 4062 0100",
        "Swift/BIC": "BRELROBUXXX"
    },
    "SEK": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "SGD": [
        {
            "Account number": "986-440-6",
            "Bank code": "0516",
            "Swift/BIC": "TRWISGSGXXX",
            "Note": "FAST Network"
        },
        {
            "Account number": "885-074-245-458",
            "Bank code": "7171",
            "Swift/BIC": "TRWISGSGXXX",
            "Note": "DBS Bank Ltd - Large Amounts"
        }
    ],
    "TRY": {
        "IBAN": "TR22 0010 3000 0000 0057 5537 17",
        "Bank name": "Fibabanka A.Ş."
    },
    "UGX": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    },
    "USD": {
        "Account number": "8313578108",
        "Routing number (ACH or ABA)": "026073150",
        "Wire routing number": "026073150",
        "Swift/BIC": "CMFGUS33"
    },
    "ZAR": {
        "IBAN": "GB72 TRWI 2314 7072 6009 80",
        "Swift/BIC": "TRWIGB2LXXX"
    }
}


def generate_invoice_number():
    return f"INV-{random.randint(1000000, 9999999)}"

def create_payment_intent(amount, currency, payment_method_type, invoice_number, description):
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=currency,
            payment_method_types=[payment_method_type],
            metadata={
                'invoice_number': invoice_number,
                'description': description
            },
            automatic_payment_methods={"enabled": True, "allow_redirects": "always"}
        )
        return intent
    except stripe.error.StripeError as e:
        st.error(f"Error creating PaymentIntent: {str(e)}")
        return None

def estimate_stripe_fees(amount, currency):
    if currency == 'USD':
        return round(amount * 0.029 + 0.30, 2)
    else:
        return round(amount * 0.039 + 0.30, 2)

def estimate_clearance_time(currency):
    standard_times = {
        "USD": "2-3 business days",
        "EUR": "2-3 business days",
        "GBP": "2-3 business days",
        "JPY": "3-5 business days",
        "CAD": "2-3 business days",
        "AUD": "2-3 business days",
        "CHF": "3-5 business days",
        "CNY": "3-5 business days",
        "HKD": "3-5 business days",
        "SGD": "3-5 business days"
    }
    return standard_times.get(currency, "5-7 business days")

def display_bank_transfer_fields(currency):
    fields = {}
    fields["Account holder"] = st.text_input("Account holder")
    if currency in BANK_TRANSFER_REQUIREMENTS:
        for field in BANK_TRANSFER_REQUIREMENTS[currency]:
            value = st.text_input(field)
            fields[field] = value
            if field == "IBAN" and "BIC/SWIFT" in BANK_TRANSFER_REQUIREMENTS[currency]:
                st.warning("SWIFT is for cross-border transactions which will take longer to clear.")
    else:
        st.warning(f"Bank transfer details for {currency} are not available. Please contact support for assistance.")
    return fields

def create_wise_transfer(source_currency, target_currency, amount, account_details, invoice_number):
    headers = {
        "Authorization": f"Bearer {WISE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    quote_data = {
        "sourceCurrency": source_currency,
        "targetCurrency": target_currency,
        "sourceAmount": amount
    }
    quote_response = requests.post(f"{WISE_API_URL}/v2/quotes", headers=headers, json=quote_data)
    quote = quote_response.json()
    
    account_data = {
        "currency": target_currency,
        "type": "iban",  # Adjust based on the account type
        "details": account_details
    }
    account_response = requests.post(f"{WISE_API_URL}/v1/accounts", headers=headers, json=account_data)
    account = account_response.json()
    
    transfer_data = {
        "targetAccount": account["id"],
        "quoteUuid": quote["id"],
        "customerTransactionId": invoice_number,
        "details": {
            "reference": "Advisory Services"
        }
    }
    transfer_response = requests.post(f"{WISE_API_URL}/v1/transfers", headers=headers, json=transfer_data)
    transfer = transfer_response.json()
    
    return transfer

def check_wise_transfer_status(transfer_id):
    headers = {
        "Authorization": f"Bearer {WISE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{WISE_API_URL}/v1/transfers/{transfer_id}", headers=headers)
    transfer = response.json()
    
    status_descriptions = {
        "incoming_payment_waiting": "On its way to Wise",
        "incoming_payment_initiated": "On its way to Wise",
        "processing": "Processing",
        "funds_converted": "Processing",
        "outgoing_payment_sent": "Sent",
        "charged_back": "Charged back",
        "cancelled": "Cancelled",
        "funds_refunded": "Refunded",
        "bounced_back": "Bounced back",
        "unknown": "Unknown"
    }
    
    return status_descriptions.get(transfer['status'], "Unknown status")

def get_wise_deposit_details(transfer_id):
    headers = {
        "Authorization": f"Bearer {WISE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{WISE_API_URL}/v1/profiles/{WISE_PROFILE_ID}/transfers/{transfer_id}/deposit-details/bank-transfer", headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error retrieving deposit details: {response.text}")
        return None

def main():
    st.title("Avuant Advisory Services")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Make Payment", "Track Payment", "Pre-authorization", "Bank Account Details", "Track Wise Transfer"])

    with tab1:
        st.header("Payment Details")
        
        invoice_number = generate_invoice_number()
        description = "Advisory Services"
        
        st.write(f"Invoice Number: {invoice_number}")
        st.write(f"Description: {description}")

        currency = st.selectbox("Select Currency", list(CURRENCIES.keys()), 
                                format_func=lambda x: f"{x} - {CURRENCIES[x]}")

        amount = st.number_input("Amount", min_value=0.01, step=0.01, value=10.00)

        if amount > 0:
            estimated_fee = estimate_stripe_fees(amount, currency)
            clearance_time = estimate_clearance_time(currency)
            st.write(f"Estimated Stripe fee: {estimated_fee} {currency}")
            st.write(f"Total amount (including fee): {amount + estimated_fee} {currency}")
            st.write(f"Estimated clearance time: {clearance_time}")

        payment_method = st.radio("Select Payment Method", ["Credit/Debit Card", "Bank Transfer"])

        if payment_method == "Credit/Debit Card":
            st.subheader("Enter Card Details")
            card_number = st.text_input("Card Number")
            exp_month = st.text_input("Expiration Month (MM)")
            exp_year = st.text_input("Expiration Year (YYYY)")
            cvc = st.text_input("CVC")
            stripe_payment_method = "card"
        else:
            st.subheader("Enter Bank Account Details")
            bank_fields = display_bank_transfer_fields(currency)
            stripe_payment_method = "customer_balance"

        if st.button("Confirm Payment"):
            payment_intent = create_payment_intent(amount, currency, stripe_payment_method, invoice_number, description)
            
            if payment_intent:
                st.success("Payment Intent created successfully!")
                st.json(payment_intent)
                st.info(f"Use this Client Secret to complete the payment: {payment_intent.client_secret}")
                st.info(f"Your invoice number is: {invoice_number}. Please save this for tracking your payment.")

                if payment_method == "Bank Transfer":
                    st.warning("For bank transfers, please use the payment instructions provided by our support team to complete the transaction.")

                # Additional message output for payment confirmation
                status = check_payment_status(invoice_number)
                st.write(f"Payment Status: {status}")

    with tab2:
        st.header("Track Your Payment or Pre-authorization")
        tracking_invoice_number = st.text_input("Enter your invoice number")
        if st.button("Track Payment/Pre-authorization"):
            if tracking_invoice_number:
                status = check_payment_status(tracking_invoice_number)
                st.write(f"Status: {status}")
            else:
                st.warning("Please enter an invoice number to track your payment or pre-authorization.")

    with tab3:
        st.header("Pre-authorization")
        st.write("Pre-authorize a payment amount without capturing it immediately.")
        
        st.warning("⚠️ Important: The pre-authorization will expire in 7 days if not captured. After expiration, the funds will be released back to the card holder.")

        preauth_amount = st.number_input("Pre-authorization Amount", min_value=0.01, step=0.01, value=10.00)
        preauth_currency = st.selectbox("Select Currency for Pre-authorization", list(CURRENCIES.keys()), 
                                        format_func=lambda x: f"{x} - {CURRENCIES[x]}")

        st.subheader("Enter Card Details for Pre-authorization")
        preauth_card_number = st.text_input("Card Number", key="preauth_card_number")
        preauth_exp_month = st.text_input("Expiration Month (MM)", key="preauth_exp_month")
        preauth_exp_year = st.text_input("Expiration Year (YYYY)", key="preauth_exp_year")
        preauth_cvc = st.text_input("CVC", key="preauth_cvc")

        if st.button("Pre-authorize Payment"):
            preauth_invoice_number = generate_invoice_number()
            preauth_description = "Pre-authorized Payment"

            preauth_intent = create_payment_intent(preauth_amount, preauth_currency, "card", preauth_invoice_number, preauth_description)

            if preauth_intent:
                st.success("Pre-authorization successful!")
                st.json(preauth_intent)
                st.info(f"Pre-authorization Invoice Number: {preauth_invoice_number}")
                
                st.write(f"Pre-authorization Status: {preauth_intent.status}")
                expiration_date = datetime.now() + timedelta(days=7)
                st.write(f"Pre-authorization Expiration Date: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}")
                
                st.warning("Remember: This pre-authorization will expire in 7 days if not captured. After expiration, the funds will be released.")
                st.info(f"You can track the status of your pre-authorization using the invoice number: {preauth_invoice_number}")

    with tab4:
        st.header("Bank Account Details and Direct Deposit")
        st.warning("This is for direct bank deposit. You can view our account details or initiate a transfer.")
        
        selected_currency = st.selectbox("Select Currency", list(BANK_ACCOUNT_DETAILS.keys()))
        
        st.subheader(f"Account Details for {selected_currency}")
        st.write("Account Name: Auvant Advisory Services")
        
        # Retrieve Wise deposit details
        wise_deposit_details = get_wise_deposit_details(WISE_PROFILE_ID)
        
        if wise_deposit_details:
            st.write("Bank Name:", wise_deposit_details['payinBank']['bankName'])
            st.write("Bank Address:", wise_deposit_details['payinBank']['bankAddress']['firstLine'], 
                     wise_deposit_details['payinBank']['bankAddress']['city'], 
                     wise_deposit_details['payinBank']['bankAddress']['postCode'], 
                     wise_deposit_details['payinBank']['bankAddress']['countryName'])
            
            st.subheader("Account Details")
            for detail in wise_deposit_details['payinBankAccount']['details']:
                st.write(f"{detail['label']}: {detail['value']}")
                if detail['type'] == 'iban' and any(d['type'] == 'bic' for d in wise_deposit_details['payinBankAccount']['details']):
                    st.warning("SWIFT is for cross-border transactions which will take longer to clear.")
        else:
            st.error("Unable to retrieve Wise deposit details. Please try again later.")
        
        st.subheader("Initiate Direct Deposit")
        st.write("Enter your banking details to initiate a transfer to our account.")
        
        source_currency = st.selectbox("Your Currency", list(CURRENCIES.keys()), key="source_currency")
        amount = st.number_input("Amount to Transfer", min_value=0.01, step=0.01, value=100.00)
        
        # Collect user's banking details
        st.write("Your Banking Details:")
        bank_fields = display_bank_transfer_fields(source_currency)
        
        if st.button("Initiate Transfer"):
            if all(bank_fields.values()):
                invoice_number = generate_invoice_number()
                try:
                    transfer = create_wise_transfer(source_currency, selected_currency, amount, bank_fields, invoice_number)
                    st.success(f"Transfer initiated successfully! Transfer ID: {transfer['id']}")
                    st.info(f"Your invoice number is: {invoice_number}. Please save this for tracking your transfer.")
                    st.json(transfer)
                except Exception as e:
                    st.error(f"An error occurred while initiating the transfer: {str(e)}")
            else:
                st.warning("Please fill in all required banking details.")

    with tab5:
        st.header("Track Wise Transfer")
        st.write("Enter your invoice number to track your Wise transfer.")
        
        tracking_invoice_number = st.text_input("Enter your invoice number")
        if st.button("Track Wise Transfer"):
            if tracking_invoice_number:
                # In a real scenario, you'd need to store and retrieve the transfer ID associated with the invoice number
                # For this example, we'll assume the transfer ID is the same as the invoice number
                status = check_wise_transfer_status(tracking_invoice_number)
                st.write(f"Transfer Status: {status}")
                
                if status == "Sent":
                    st.success("Your transfer has been sent successfully!")
                elif status in ["Cancelled", "Refunded", "Charged back"]:
                    st.error(f"Your transfer has been {status.lower()}. Please contact support for assistance.")
                elif status == "Bounced back":
                    st.warning("Your transfer has bounced back. It may be delivered with a delay or refunded.")
                else:
                    st.info(f"Your transfer is currently {status.lower()}. Please check back later for updates.")
            else:
                st.warning("Please enter an invoice number to track your transfer.")

if __name__ == "__main__":
    main()
