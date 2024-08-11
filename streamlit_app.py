import streamlit as st
import stripe
import random
from datetime import datetime, timedelta
import requests
import json
import logging
import uuid

# Configure logging
logging.basicConfig(level=st.secrets.app_settings.log_level)
logger = logging.getLogger(__name__)

# Initialize Stripe API key
stripe.api_key = st.secrets.stripe.stripe_api_key

# Debug mode setting
DEBUG_MODE = st.secrets.app_settings.debug_mode

# Default currency options
DEFAULT_SOURCE_CURRENCY = st.secrets.currency_options.default_source
DEFAULT_TARGET_CURRENCY = st.secrets.currency_options.default_target

# Add the CURRENCIES dictionary
CURRENCIES = {
    "AED": "United Arab Emirates Dirham",
    "AUD": "Australian Dollar",
    "BGN": "Bulgarian Lev",
    "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc",
    "CNY": "Chinese Yuan",
    "CZK": "Czech Koruna",
    "DKK": "Danish Krone",
    "EUR": "Euro",
    "GBP": "British Pound",
    "HKD": "Hong Kong Dollar",
    "HUF": "Hungarian Forint",
    "ILS": "Israeli Shekel",
    "NOK": "Norwegian Krone",
    "NZD": "New Zealand Dollar",
    "PLN": "Polish Zloty",
    "RON": "Romanian Leu",
    "SEK": "Swedish Krona",
    "SGD": "Singapore Dollar",
    "TRY": "Turkish Lira",
    "UGX": "Ugandan Shilling",
    "USD": "United States Dollar",
    "ZAR": "South African Rand"
}

# Pre-defined account details (without Swift/BIC)
ACCOUNT_DETAILS = {
    "AED": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "AUD": {"Account number": "208236946", "BSB code": "774-001"},
    "BGN": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "CAD": {"Account number": "200110754005", "Institution number": "621", "Transit number": "16001"},
    "CHF": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "CNY": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "CZK": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "DKK": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "EUR": {"IBAN": "BE60 9677 1622 9370"},
    "GBP": {"Account number": "72600980", "UK sort code": "23-14-70", "IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "HKD": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "HUF": {"Account number": "12600016-16459316-39343647", "IBAN": "HU74 1260 0016 1645 9316 3934 3647"},
    "ILS": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "NOK": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "NZD": {"Account number": "04-2021-0152352-80"},
    "PLN": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "RON": {"Account number": "RO25 BREL 0005 6019 4062 0100"},
    "SEK": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "SGD": {"Account number": "885-074-245-458", "Bank code": "7171"},
    "TRY": {"IBAN": "TR22 0010 3000 0000 0057 5537 17"},
    "UGX": {"IBAN": "GB72 TRWI 2314 7072 6009 80"},
    "USD": {"Account number": "8313578108", "Routing number (ACH or ABA)": "026073150", "Wire routing number": "026073150"},
    "ZAR": {"IBAN": "GB72 TRWI 2314 7072 6009 80"}
}

def generate_invoice_number():
    return f"INV-{random.randint(1000000, 9999999)}"

def create_payment_intent(amount, currency, description, invoice_number):
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Amount in cents
            currency=currency,
            description=description,
            metadata={
                'invoice_number': invoice_number
            },
            automatic_payment_methods={"enabled": True}
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

def check_payment_status(identifier):
    try:
        payment_intents = stripe.PaymentIntent.list(metadata={'invoice_number': identifier})
        if payment_intents.data:
            payment_intent = payment_intents.data[0]
            return f"Payment Status: {payment_intent.status}", None
    except stripe.error.StripeError as e:
        return f"Error checking payment status: {str(e)}", None

    return "No payment found with this identifier.", None

def main():
    st.title("Auvant Advisory Services")

    if DEBUG_MODE:
        st.sidebar.write("Debug Information:")
        st.sidebar.write(f"Stripe API Key: {stripe.api_key[:10]}...")
        st.sidebar.write(f"Default Source Currency: {DEFAULT_SOURCE_CURRENCY}")
        st.sidebar.write(f"Default Target Currency: {DEFAULT_TARGET_CURRENCY}")

    tab1, tab2, tab3, tab4 = st.tabs(["Make Payment", "Track Payment", "Pre-authorization", "Direct Bank Deposit"])

    with tab1:
        st.header("Payment Details")
        
        invoice_number = generate_invoice_number()
        description = "Advisory Services"
        
        st.write(f"Invoice Number: {invoice_number}")
        st.write(f"Description: {description}")

        currency = st.selectbox("Select Currency", list(CURRENCIES.keys()), 
                                index=list(CURRENCIES.keys()).index(DEFAULT_SOURCE_CURRENCY),
                                format_func=lambda x: f"{x} - {CURRENCIES[x]}")

        amount = st.number_input("Amount", min_value=0.01, step=0.01, value=10.00, key="tab1_amount")

        if amount > 0:
            estimated_fee = estimate_stripe_fees(amount, currency)
            clearance_time = estimate_clearance_time(currency)
            st.write(f"Estimated Stripe fee: {estimated_fee} {currency}")
            st.write(f"Total amount (including fee): {amount + estimated_fee} {currency}")
            st.write(f"Estimated clearance time: {clearance_time}")

        payment_method = st.radio("Select Payment Method", ["Credit/Debit Card", "Bank Transfer"], key="tab1_payment_method")

        if payment_method == "Credit/Debit Card":
            st.subheader("Enter Card Details")
            st.write("Card details will be collected securely by Stripe.")
        else:
            st.subheader("Bank Transfer")
            st.info("For bank transfers, please use the details provided in the 'Direct Bank Deposit' tab.")

        if st.button("Confirm Payment", key="tab1_confirm_payment"):
            payment_intent = create_payment_intent(amount, currency, description, invoice_number)
            
            if payment_intent:
                st.success("Payment Intent created successfully!")
                st.json(payment_intent)
                st.info(f"Use this Client Secret to complete the payment: {payment_intent.client_secret}")
                st.info(f"Your invoice number is: {invoice_number}. Please save this for tracking your payment.")

                if payment_method == "Bank Transfer":
                    st.warning("For bank transfers, please use the payment instructions provided in the 'Direct Bank Deposit' tab.")

                status, _ = check_payment_status(invoice_number)
                st.write(f"Payment Status: {status}")
                
    with tab2:
        st.header("Track Your Payment")
        tracking_identifier = st.text_input("Enter your invoice number or transfer ID", key="tab2_tracking_identifier")
        if st.button("Track Payment", key="tab2_track_payment"):
            if tracking_identifier:
                status, _ = check_payment_status(tracking_identifier)
                st.write(f"Status: {status}")
                
                if "succeeded" in status.lower():
                    st.success("Your payment has been processed successfully!")
                elif any(state in status.lower() for state in ["canceled", "refunded"]):
                    st.error(f"Your payment has been {status.lower()}. Please contact support for assistance.")
                else:
                    st.info(f"Your payment is currently being processed. Please check back later for updates.")
            else:
                st.warning("Please enter an invoice number or transfer ID to track your payment.")

    with tab3:
        st.header("Pre-authorization")
        st.write("Pre-authorize a payment amount without capturing it immediately.")
        
        st.warning("⚠️ Important: The pre-authorization will expire in 7 days if not captured. After expiration, the funds will be released back to the card holder.")

        preauth_amount = st.number_input("Pre-authorization Amount", min_value=0.01, step=0.01, value=10.00, key="tab3_preauth_amount")
        preauth_currency = st.selectbox("Select Currency for Pre-authorization", list(CURRENCIES.keys()), 
                                        index=list(CURRENCIES.keys()).index(DEFAULT_SOURCE_CURRENCY),
                                        format_func=lambda x: f"{x} - {CURRENCIES[x]}", 
                                        key="tab3_preauth_currency")

        st.subheader("Enter Card Details for Pre-authorization")
        preauth_card_number = st.text_input("Card Number", key="tab3_card_number")
        preauth_exp_month = st.text_input("Expiration Month (MM)", key="tab3_exp_month")
        preauth_exp_year = st.text_input("Expiration Year (YYYY)", key="tab3_exp_year")
        preauth_cvc = st.text_input("CVC", key="tab3_cvc")

        if st.button("Pre-authorize Payment", key="tab3_preauth_payment"):
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
        st.header("Direct Bank Deposit to Our Wise Account")
        st.info("This section provides our Wise account details for direct deposit. Select a currency to view the corresponding account information.")

        # Select currency
        available_currencies = list(ACCOUNT_DETAILS.keys())
        selected_currency = st.selectbox('Select Currency', available_currencies, 
                                         format_func=lambda x: f"{x} - {CURRENCIES.get(x, x)}", 
                                         key="tab4_currency")

        if selected_currency in ACCOUNT_DETAILS:
            # Generate invoice number and transfer ID
            if 'invoice_number' not in st.session_state:
                st.session_state.invoice_number = generate_invoice_number()
            if 'transfer_id' not in st.session_state:
                st.session_state.transfer_id = f"WT-{random.randint(1000000, 9999999)}"

            st.subheader(f"Our Wise Account Details for {selected_currency}")
            st.write("Account Name: Auvant Advisory Services")
            
            our_bank_details = ACCOUNT_DETAILS[selected_currency]
            for key, value in our_bank_details.items():
                if 'Swift' not in key and 'BIC' not in key:
                    st.write(f"{key}: {value}")
            
            st.info(f"Your Invoice Number: {st.session_state.invoice_number}")
            st.info(f"Your Transfer ID: {st.session_state.transfer_id}")
            
            st.warning("""
            Keep these details to track the transaction.
            You will need to make the direct deposit from your own bank.
            """)
            
            st.subheader("Steps to Complete Your Deposit:")
            st.markdown("""
            1. Log in to your bank's online banking platform.
            2. Navigate to the international transfer or wire transfer section.
            3. Enter the account details provided above as the recipient's information.
            4. Enter the amount you wish to transfer.
            5. In the reference or description field, please include your Transfer ID.
            6. Review all details carefully before confirming the transfer.
            7. Once completed, keep your bank's transaction confirmation for your records.
            """)

            st.info("Use your Transfer ID to track this deposit in the 'Track Payment' tab.")
            
            # Optional: Allow user to enter transfer amount for record-keeping
            amount = st.number_input("Amount to Transfer (for your records only)", min_value=0.01, step=0.01, value=100.00, key="tab4_amount")
            
            if st.button("Save Transfer Details", key="tab4_save_details"):
                # Here you would typically save these details to a database
                # For this example, we'll just display a confirmation
                st.success("Transfer details saved successfully!")
                st.json({
                    "invoice_number": st.session_state.invoice_number,
                    "transfer_id": st.session_state.transfer_id,
                    "currency": selected_currency,
                    "amount": amount
                })
                st.info("Please proceed with the transfer using your bank's system and the provided account details.")
        else:
            st.error(f"Account details for {selected_currency} are not available. Please contact support for assistance.")

if __name__ == "__main__":
    main()
