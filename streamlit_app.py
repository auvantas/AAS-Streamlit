import streamlit as st
import stripe
import random
from datetime import datetime, timedelta
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=st.secrets.app_settings.log_level)
logger = logging.getLogger(__name__)

# Initialize Stripe and Wise API keys
stripe.api_key = st.secrets.stripe.stripe_api_key
WISE_API_KEY = st.secrets.wise.WISE_API_KEY
WISE_API_URL = "https://api.transferwise.com"
WISE_PROFILE_ID = st.secrets.wise.profile_id

# Debug mode setting
DEBUG_MODE = st.secrets.app_settings.debug_mode

# Default currency options
DEFAULT_SOURCE_CURRENCY = st.secrets.currency_options.default_source
DEFAULT_TARGET_CURRENCY = st.secrets.currency_options.default_target

# ... (keep the existing CURRENCIES and BANK_TRANSFER_REQUIREMENTS dictionaries)

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

def display_bank_transfer_fields(currency, prefix):
    fields = {}
    fields["Account holder"] = st.text_input("Account holder", key=f"{prefix}_account_holder")
    if currency in BANK_TRANSFER_REQUIREMENTS:
        for field in BANK_TRANSFER_REQUIREMENTS[currency]:
            value = st.text_input(field, key=f"{prefix}_{field.lower().replace(' ', '_')}")
            fields[field] = value
            if field == "IBAN" and "BIC/SWIFT" in BANK_TRANSFER_REQUIREMENTS[currency]:
                st.warning("SWIFT is for cross-border transactions which will take longer to clear.")
    else:
        st.warning(f"Bank transfer details for {currency} are not available. Please contact support for assistance.")
    return fields

def create_wise_transfer(source_currency, target_currency, amount, account_details):
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
        "customerTransactionId": str(random.randint(1000000000, 9999999999)),
        "details": {
            "reference": "Advisory Services"
        }
    }
    transfer_response = requests.post(f"{WISE_API_URL}/v1/transfers", headers=headers, json=transfer_data)
    transfer = transfer_response.json()
    
    return transfer

def check_payment_status(identifier):
    # First, check Stripe payment status
    try:
        payment_intents = stripe.PaymentIntent.list(metadata={'invoice_number': identifier})
        if payment_intents.data:
            payment_intent = payment_intents.data[0]
            return f"Stripe Payment Status: {payment_intent.status}", None
    except stripe.error.StripeError as e:
        return f"Error checking Stripe payment status: {str(e)}", None

    # If not found in Stripe, check Wise transfer status
    try:
        headers = {
            "Authorization": f"Bearer {WISE_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.get(f"{WISE_API_URL}/v1/transfers/{identifier}", headers=headers)
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
        return f"Wise Transfer Status: {status_descriptions.get(transfer['status'], 'Unknown status')}", transfer['id']
    except Exception as e:
        return f"Error checking Wise transfer status: {str(e)}", None

    return "No payment or transfer found with this identifier.", None

def get_delivery_estimate(transfer_id):
    headers = {
        "Authorization": f"Bearer {WISE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{WISE_API_URL}/v1/delivery-estimates/{transfer_id}", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        estimated_delivery_date = datetime.fromisoformat(data['estimatedDeliveryDate'].replace('Z', '+00:00'))
        return estimated_delivery_date
    else:
        st.error(f"Error retrieving delivery estimate: {response.text}")
        return None

def get_wise_deposit_details(profile_id, currency):
    headers = {
        "Authorization": f"Bearer {WISE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(f"{WISE_API_URL}/v1/profiles/{profile_id}/borderless-accounts", headers=headers)
    
    if response.status_code == 200:
        accounts = response.json()
        for account in accounts:
            for balance in account['balances']:
                if balance['currency'] == currency:
                    return balance['bankDetails']
        return None
    else:
        st.error(f"Error retrieving deposit details: {response.text}")
        return None

def main():
    st.title("Avuant Advisory Services")

    # Display debug information if in debug mode
    if DEBUG_MODE:
        st.sidebar.write("Debug Information:")
        st.sidebar.write(f"Stripe API Key: {stripe.api_key[:10]}...")
        st.sidebar.write(f"Wise Profile ID: {WISE_PROFILE_ID}")
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
            card_number = st.text_input("Card Number", key="tab1_card_number")
            exp_month = st.text_input("Expiration Month (MM)", key="tab1_exp_month")
            exp_year = st.text_input("Expiration Year (YYYY)", key="tab1_exp_year")
            cvc = st.text_input("CVC", key="tab1_cvc")
            stripe_payment_method = "card"
        else:
            st.subheader("Enter Bank Account Details")
            bank_fields = display_bank_transfer_fields(currency, "tab1")
            stripe_payment_method = "customer_balance"

        if st.button("Confirm Payment", key="tab1_confirm_payment"):
            payment_intent = create_payment_intent(amount, currency, stripe_payment_method, invoice_number, description)
            
            if payment_intent:
                st.success("Payment Intent created successfully!")
                st.json(payment_intent)
                st.info(f"Use this Client Secret to complete the payment: {payment_intent.client_secret}")
                st.info(f"Your invoice number is: {invoice_number}. Please save this for tracking your payment.")

                if payment_method == "Bank Transfer":
                    st.warning("For bank transfers, please use the payment instructions provided by our support team to complete the transaction.")

                # Additional message output for payment confirmation
                status, _ = check_payment_status(invoice_number)
                st.write(f"Payment Status: {status}")

    with tab2:
        st.header("Track Your Payment or Transfer")
        tracking_identifier = st.text_input("Enter your invoice number or transfer ID", key="tab2_tracking_identifier")
        if st.button("Track Payment/Transfer", key="tab2_track_payment"):
            if tracking_identifier:
                status, transfer_id = check_payment_status(tracking_identifier)
                st.write(f"Status: {status}")
                
                if "Sent" in status and transfer_id:
                    estimated_delivery = get_delivery_estimate(transfer_id)
                    if estimated_delivery:
                        st.success(f"Estimated delivery date: {estimated_delivery.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    else:
                        st.warning("Unable to retrieve estimated delivery date.")
                
                if "Sent" in status:
                    st.success("Your payment/transfer has been sent successfully!")
                elif any(state in status for state in ["Cancelled", "Refunded", "Charged back"]):
                    st.error(f"Your payment/transfer has encountered an issue. Please contact support for assistance.")
                elif "Bounced back" in status:
                    st.warning("Your transfer has bounced back. It may be delivered with a delay or refunded.")
                else:
                    st.info(f"Your payment/transfer is currently being processed. Please check back later for updates.")
            else:
                st.warning("Please enter an invoice number or transfer ID to track your payment or transfer.")

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
        st.header("Direct Bank Deposit")
        st.warning("This is for direct bank deposit which is quicker than using Stripe. You can view our account details or initiate a transfer.")
        
        available_currencies = list(CURRENCIES.keys())
        selected_currency = st.selectbox("Select Currency for Deposit", available_currencies, key="tab4_currency")
        
        wise_deposit_details = get_wise_deposit_details(WISE_PROFILE_ID, selected_currency)
        
        if wise_deposit_details:
            st.subheader(f"Account Details for {selected_currency}")
            st.write("Account Name: Auvant Advisory Services")
            
            for key, value in wise_deposit_details.items():
                if key != 'accountType':  # We don't need to show the account type
                    st.write(f"{key.capitalize()}: {value}")
            
            if 'IBAN' in wise_deposit_details and 'SWIFT' in wise_deposit_details:
                st.warning("SWIFT is for cross-border transactions which will take longer to clear.")
            
            st.subheader("Initiate Direct Deposit")
            st.write("Enter your banking details to initiate a transfer to our account.")
            
            amount = st.number_input("Amount to Transfer", min_value=0.01, step=0.01, value=100.00, key="tab4_amount")
            
            # Collect user's banking details
            st.write("Your Banking Details:")
            bank_fields = display_bank_transfer_fields(selected_currency, "tab4")
            
            if st.button("Initiate Transfer", key="tab4_initiate_transfer"):
                if all(bank_fields.values()):
                    try:
                        transfer = create_wise_transfer(selected_currency, selected_currency, amount, bank_fields)
                        st.success(f"Transfer initiated successfully!")
                        st.info(f"Your Wise Transfer ID is: {transfer['id']}. Please save this for tracking your transfer.")
                        st.json(transfer)
                    except Exception as e:
                        st.error(f"An error occurred while initiating the transfer: {str(e)}")
                else:
                    st.warning("Please fill in all required banking details.")
        else:
            st.error(f"Unable to retrieve deposit details for {selected_currency}. Please try again later or contact support.")

if __name__ == "__main__":
    main()
