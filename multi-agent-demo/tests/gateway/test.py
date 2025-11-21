import requests
response = requests.post(
    'https://ap-southeast-1riin9nobk.auth.ap-southeast-1.amazoncognito.com/oauth2/token',
    data="grant_type=client_credentials&client_id=4qe3tcl6st884iidhv7jdgha54&client_secret=14dj36m1gbm1d6ngd25qntoonanmns6tht6g81cva13s38dlujcm&scope=default-m2m-resource-server-yryktv/read",
    headers={'Content-Type': 'application/x-www-form-urlencoded'}
)
print(response.json())