from django.http import JsonResponse

def simulate(request):
    # Simulate an API response
    return JsonResponse({'message': 'Simulated response'})

def setup(request):
    # Handle simulator setup
    return JsonResponse({'message': 'Simulator setup complete'})
