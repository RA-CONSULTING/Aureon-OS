"""
Prime Web Validator and Optimizer

This script implements and optimizes a conceptual framework for creating a stable 
"web" of connections between nodes, using prime numbers for node IDs and 
connection rules.

- It searches for an optimal set of 10 primes that maximizes connectivity.
- A connection (link) is formed if the absolute difference or the sum 
  of their prime IDs is also a prime number.
- The script then builds and displays the most robust web found.
"""

import math
from itertools import combinations

def is_prime(n):
    """Checks if a number is prime."""
    if n <= 1: return False
    if n <= 3: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0: return False
        i += 6
    return True

def generate_primes(count, start_after=0):
    """Generates 'count' prime numbers after a certain number."""
    primes = []
    num = start_after + 1
    while len(primes) < count:
        if is_prime(num):
            primes.append(num)
        num += 1
    return primes

def calculate_connectivity_score(nodes):
    """Calculates a score based on web density and penalties for isolation."""
    links = 0
    isolated_nodes = 0
    link_map = {p: 0 for p in nodes}

    for p1, p2 in combinations(nodes, 2):
        if is_prime(abs(p1 - p2)) or is_prime(p1 + p2):
            links += 1
            link_map[p1] += 1
            link_map[p2] += 1
    
    for node in nodes:
        if link_map[node] == 0:
            isolated_nodes += 1
            
    # Score: Total links minus a heavy penalty for any isolated nodes.
    # This prioritizes webs with no isolated pillars.
    score = links - (isolated_nodes * 100)
    return score, links, isolated_nodes

def find_optimal_prime_set(search_space=25, set_size=10):
    """Searches for the best set of primes to form a robust web."""
    print(f"Searching for an optimal set of {set_size} primes from the first {search_space} primes...")
    primes_to_search = generate_primes(search_space)
    
    best_set = None
    best_score = -float('inf')
    
    # Test all combinations of `set_size` primes from the search space
    for prime_set in combinations(primes_to_search, set_size):
        score, _, _ = calculate_connectivity_score(prime_set)
        if score > best_score:
            best_score = score
            best_set = list(prime_set)
            
    print(f"Found optimal set with score {best_score}: {best_set}")
    return best_set

def build_prime_web(nodes):
    """Builds and displays the prime web for a given set of nodes."""
    print(f"\n--- Building Prime Web for Nodes: {nodes} ---")
    web = {p: [] for p in nodes}
    edges = set()
    for p1, p2 in combinations(nodes, 2):
        if is_prime(abs(p1 - p2)) or is_prime(p1 + p2):
            web[p1].append(p2)
            web[p2].append(p1)
            edges.add(tuple(sorted((p1, p2))))

    central_lock_hash = hash(frozenset(edges))
    total_links = len(edges)
    
    print("\n--- Optimal Prime Web Structure (10-9-1 Lock Metric) ---")
    for node, links in sorted(web.items()):
        print(f"Node {node:2d}: Links ({len(links):2d}) -> {sorted(links)}")
        if not links:
            print(f"  [CRITICAL] Node {node} is ISOLATED.")

    print(f"\nTotal connections in the web: {total_links}")
    print(f"Average links per node: {total_links * 2 / len(nodes):.2f}")
    print(f"Central Lock Verification Hash: {central_lock_hash}")
    print("--- Validation Complete ---")

if __name__ == "__main__":
    # 1. Find the best set of 10 primes from the first 25 primes.
    #    (A larger search space could yield better results but takes more time)
    optimal_nodes = find_optimal_prime_set(search_space=30, set_size=10)
    
    # 2. Build and display the web using this optimal set.
    if optimal_nodes:
        build_prime_web(optimal_nodes)
    else:
        print("Could not find an optimal prime set.")
