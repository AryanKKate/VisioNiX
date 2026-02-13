import faiss
import numpy as np
import os

dimension = 512
index = faiss.IndexFlatL2(dimension)

metadata = []

def add_vector(vector, data):
    vec = np.array(vector).astype("float32")
    index.add(np.expand_dims(vec, axis=0))
    metadata.append(data)

def search_vector(vector, k=5):
    vec = np.array(vector).astype("float32")
    D, I = index.search(np.expand_dims(vec, axis=0), k)
    results = [metadata[i] for i in I[0]]
    return results
