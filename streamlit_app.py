import streamlit as st
import stripe
from datetime import datetime, timedelta
from flask import Flask, request, jsonify

# Access configuration values from Streamlit secrets
STRIPE_API_KEY = st.secrets["stripe"]["api_key"]
STRIPE_WEBHOOK_SECRET = st.secrets["stripe"]["webhook_secret"]

# Initialize Stripe client
stripe.api_key = STRIPE_API_KEY

# Initialize Flask app for webhook handling
flask_app = Flask(__name__)

# Updated currencies supported by Stripe
CURRENCIES = {
    "BGN": "Bulgarian Lev - Bulgaria",
    "CAD": "Canadian Dollar - Canada",
    "CHF": "Swiss Franc - Switzerland and Liechtenstein",
    "CNY": "Chinese Yuan - China (via China UnionPay for card payments)",
    "CZK": "Czech Koruna - Czech Republic",
    "DKK": "Danish Krone - Denmark",
    "EUR": "Euro - Multiple European countries",
    "GBP": "British Pound - United Kingdom",
    "HKD": "Hong Kong Dollar - Hong Kong",
    "HUF": "Hungarian Forint - Hungary",
    "NOK": "Norwegian Krone - Norway",
    "NZD": "New Zealand Dollar - New Zealand",
    "PLN": "Polish Zloty - Poland",
    "RON": "Romanian Leu - Romania",
    "SEK": "Swedish Krona - Sweden",
    "SGD": "Singapore Dollar - Singapore",
    "USD": "United States Dollar - United States"
}

def create_payment_intent(amount, currency, payment_method_id=None, payment_method_types=None):
    try:
        intent_params = {
            "amount": int(amount * 100),  # Stripe uses cents
            "currency": currency,
            "payment_method_types": payment_method_types or ["card"],
        }
        if payment_method_id:
            intent_params["payment_method"] = payment_method_id
            intent_params["confirm"] = True

        payment_intent = stripe.PaymentIntent.create(**intent_params)
        return payment_intent
    except stripe.error.StripeError as e:
        st.error(f"Error creating PaymentIntent: {str(e)}")
        return None

def create_bank_account_token(country, currency, account_holder_name, account_number, routing_number):
    try:
        token = stripe.Token.create(
            bank_account={
                "country": country,
                "currency": currency,
                "account_holder_name": account_holder_name,
                "account_holder_type": "individual",
                "account_number": account_number,
                "routing_number": routing_number,
            },
        )
        return token
    except stripe.error.StripeError as e:
        st.error(f"Error creating bank account token: {str(e)}")
        return None

def check_payment_status(payment_intent_id):
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return payment_intent.status
    except stripe.error.StripeError as e:
        st.error(f"Error checking payment status: {str(e)}")
        return None

# Simplified estimation (no real-time checks)
def estimate_payment_clearance(payment_intent_id):
    return "Estimated clearance: 1-2 business days"

@flask_app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return jsonify(error=str(e)), 400
    except stripe.error.SignatureVerificationError as e:
        return jsonify(error=str(e)), 400

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        print(f"Payment succeeded for PaymentIntent: {payment_intent['id']}")
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        print(f"Payment failed for PaymentIntent: {payment_intent['id']}")

    return jsonify(success=True)

def main():
    st.title("Stripe Payment App (Multi-Currency)")

    operation = st.radio("Choose operation:", ("Make a Payment", "Check Payment Status"))

    if operation == "Make a Payment":
        st.subheader("Make a Payment via Stripe")
        currency = st.selectbox("Currency", list(CURRENCIES.keys()), 
                                index=list(CURRENCIES.keys()).index('USD'),
                                format_func=lambda x: f"{x} - {CURRENCIES[x]}")
        amount = st.number_input("Amount", min_value=0.01, step=0.01)

        payment_method = st.radio("Choose payment method:", ("Credit/Debit Card", "Bank Transfer"))

        if payment_method == "Credit/Debit Card":
            st.subheader("Enter Card Details")
            card_number = st.text_input("Card Number")
            exp_month = st.text_input("Expiration Month (MM)")
            exp_year = st.text_input("Expiration Year (YYYY)")
            cvc = st.text_input("CVC")

            if st.button("Make Card Payment"):
                try:
                    payment_method = stripe.PaymentMethod.create(
                        type="card",
                        card={
                            "number": card_number,
                            "exp_month": exp_month,
                            "exp_year": exp_year,
                            "cvc": cvc,
                        },
                    )

                    payment_intent = create_payment_intent(amount, currency, payment_method.id)
                    
                    if payment_intent:
                        st.info(f"Payment status: {payment_intent.status}")
                        st.info(f"Payment Intent ID: {payment_intent.id}")
                        
                        estimated_clearance_date = estimate_payment_clearance(payment_intent.id)
                        st.info(estimated_clearance_date)
                except stripe.error.CardError as e:
                    st.error(f"Card error: {e.error.message}")
                except stripe.error.StripeError as e:
                    st.error(f"Stripe error: {str(e)}")

        else:  # Bank Transfer
            st.subheader("Enter Bank Account Details")
            account_holder_name = st.text_input("Account Holder Name")
            account_number = st.text_input("Account Number")
            routing_number = st.text_input("Routing Number")

            if st.button("Make Bank Transfer"):
                try:
                    country = "US" if currency == "USD" else "EU"
                    bank_token = create_bank_account_token(country, currency, account_holder_name, account_number, routing_number)

                    if bank_token:
                        payment_method_types = ["ach_debit"] if currency == "USD" else ["sepa_debit"]
                        payment_intent = create_payment_intent(amount, currency, bank_token.id, payment_method_types)
                        
                        if payment_intent:
                            st.info(f"Payment status: {payment_intent.status}")
                            st.info(f"Payment Intent ID: {payment_intent.id}")
                            
                            estimated_clearance_date = estimate_payment_clearance(payment_intent.id)
                            st.info(estimated_clearance_date)
                except stripe.error.StripeError as e:
                    st.error(f"Stripe error: {str(e)}")

    else:  # Check Payment Status
        st.subheader("Check Payment Status")
        payment_intent_id = st.text_input("Enter Payment Intent ID")
        if st.button("Check Status"):
            if payment_intent_id:
                status = check_payment_status(payment_intent_id)
                if status:
                    st.info(f"Payment Status: {status}")
                    estimated_clearance = estimate_payment_clearance(payment_intent_id)
                    st.info(estimated_clearance)
            else:
                st.warning("Please enter a Payment Intent ID")

if __name__ == "__main__":
    main()
