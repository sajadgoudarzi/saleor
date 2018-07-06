import json

import graphene
from django.shortcuts import reverse
from tests.utils import get_graphql_content


def test_order_query(admin_api_client, fulfilled_order):
    order = fulfilled_order
    query = """
    query OrdersQuery {
        orders(first: 1) {
            edges {
                node {
                    orderId
                    status
                    statusDisplay
                    paymentStatus
                    paymentStatusDisplay
                    userEmail
                    isPaid
                    shippingPrice {
                        gross {
                            amount
                        }
                    }
                    lines {
                        totalCount
                    }
                    notes {
                        totalCount
                    }
                    fulfillments {
                        fulfillmentOrder
                    }
                    history {
                        totalCount
                    }
                }
            }
        }
    }
    """
    response = admin_api_client.post(
        reverse('api'), {'query': query})
    content = get_graphql_content(response)
    assert 'errors' not in content
    order_data = content['data']['orders']['edges'][0]['node']
    assert order_data['orderId'] == order.pk
    assert order_data['status'] == order.status.upper()
    assert order_data['statusDisplay'] == order.get_status_display()
    assert order_data['paymentStatus'] == order.get_last_payment_status()
    payment_status_display = order.get_last_payment_status_display()
    assert order_data['paymentStatusDisplay'] == payment_status_display
    assert order_data['isPaid'] == order.is_fully_paid()
    assert order_data['userEmail'] == order.user_email
    expected_price = order_data['shippingPrice']['gross']['amount']
    assert expected_price == order.shipping_price.gross.amount
    assert order_data['lines']['totalCount'] == order.lines.count()
    assert order_data['notes']['totalCount'] == order.notes.count()
    fulfillment = order.fulfillments.first().fulfillment_order
    assert order_data['fulfillments'][0]['fulfillmentOrder'] == fulfillment


def test_non_staff_user_can_only_see_his_order(user_api_client, order):
    # FIXME: Remove client.login() when JWT authentication is re-enabled.
    user_api_client.login(username=order.user.email, password='password')

    query = """
    query OrderQuery($id: ID!) {
        order(id: $id) {
            orderId
        }
    }
    """
    ID = graphene.Node.to_global_id('Order', order.id)
    variables = json.dumps({'id': ID})
    response = user_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    content = get_graphql_content(response)
    order_data = content['data']['order']
    assert order_data['orderId'] == order.pk

    order.user = None
    order.save()
    response = user_api_client.post(
        reverse('api'), {'query': query, 'variables': variables})
    content = get_graphql_content(response)
    order_data = content['data']['order']
    assert not order_data