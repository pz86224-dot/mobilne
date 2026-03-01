import math
import matplotlib.pyplot as plt



class LCG:
    def __init__(self, seed=1):
        self.a = 16807
        self.b = 0
        self.c = 2147483647
        self.x = seed

    def gen(self):
        self.x = (self.a * self.x + self.b) % self.c
        return self.x / self.c





def poisson_generator(lam, rng):
    X = -1
    S = 1
    q = math.exp(-lam)

    while S > q:
        U = rng.gen()
        S = S * U
        X += 1

    return X




def normal_generator(mu, sigma, rng):
    U1 = rng.gen()
    U2 = rng.gen()

    Z = math.sqrt(-2 * math.log(U1)) * math.cos(2 * math.pi * U2)

    return mu + sigma * Z





def generate_samples(distribution, n, rng, **params):
    samples = []

    for _ in range(n):
        if distribution == "poisson":
            samples.append(poisson_generator(params["lam"], rng))
        elif distribution == "normal":
            samples.append(normal_generator(params["mu"], params["sigma"], rng))

    return samples



def plot_histogram(data, title, bins=100):
    plt.hist(data, bins=bins, density=True)
    plt.title(title)
    plt.xlabel("Wartość")
    plt.ylabel("Częstość")
    plt.show()


def main():
    print("Wybierz rozkład:")
    print("1 - Poissona")
    print("2 - Normalny")

    choice = input("Twój wybór: ")
    n = int(input("Ilość generowanych liczb: "))

    seed_option = input("Czy użyć ziarna? (t/n): ")

    if seed_option.lower() == "t":
        seed_value = int(input("Podaj wartość ziarna: "))
    else:
        seed_value = 1

    rng = LCG(seed_value)

    if choice == "1":
        lam = float(input("Podaj λ: "))
        data = generate_samples("poisson", n, rng, lam=lam)
        plot_histogram(
            data,
            f"Rozkład Poissona (λ={lam})",
            bins=range(min(data), max(data)+2)
        )

    elif choice == "2":
        mu = float(input("Podaj  μ: "))
        sigma = float(input("Podaj odchylenie standardowe σ: "))
        data = generate_samples("normal", n, rng, mu=mu, sigma=sigma)
        plot_histogram(
            data,
            f"Rozkład Normalny (μ={mu}, σ={sigma})"
        )

    else:
        print("Niepoprawny wybór!")


if __name__ == "__main__":
    main()