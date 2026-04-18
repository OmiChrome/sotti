import java.util.*;

/**
 * QUESTION: Generics - Complex Number Addition (Sep 2023 OPPE1, Section 1.3)
 * ============================================================================
 * Problem Statement:
 * Write a Java program to find the sum of two complex numbers. You are given
 * two integers n1, n2 and two double values d1, d2 as input, from which two
 * complex numbers c1 and c2 are obtained:
 *   - c1 has real part n1 and imaginary part n2
 *   - c2 has real part d1 and imaginary part d2
 *
 * Generic class ComplexNum<T extends Number> has:
 *   - Instance variables r and i
 *   - Constructor to initialize r and i
 *   - Method add(ComplexNum<?> c): returns the sum as ComplexNum<Double>
 *   - Method toString(): formats as "r.0 + i.0i"
 *
 * Class FClass main():
 *   - Reads two ints n1, n2 and two doubles d1, d2
 *   - Creates ComplexNum<Integer> c1 = (n1, n2) and ComplexNum<Double> c2 = (d1, d2)
 *   - Prints: c1 + " + " + c2 + " = " + c1.add(c2)
 *
 * What you have to do: Define class ComplexNum
 *
 * Test Cases:
 *   Input: 6 10 / 10.3 15.6  →  Output: 6.0 + 10.0i + 10.3 + 15.6i = 16.3 + 25.6i
 *   Input: 10 15 / 5.4 1.6   →  Output: 10.0 + 15.0i + 5.4 + 1.6i = 15.4 + 16.6i
 *   Input: 3 15 / 5.4 2.8    →  Output: 3.0 + 15.0i + 5.4 + 2.8i = 8.4 + 17.8i
 *   Input: 10 20 / 13.3 5.12 →  Output: 10.0 + 20.0i + 13.3 + 5.12i = 23.3 + 25.12i
 */

// DEFINE class ComplexNum<T extends Number> here

class Q5_FClass {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int n1, n2;
        double d1, d2;
        n1 = sc.nextInt();
        n2 = sc.nextInt();
        d1 = sc.nextDouble();
        d2 = sc.nextDouble();
        ComplexNum<Integer> c1 = new ComplexNum<Integer>(n1, n2);
        ComplexNum<Double>  c2 = new ComplexNum<Double>(d1, d2);
        ComplexNum<Double>  c3 = c1.add(c2);
        System.out.println(c1 + " + " + c2 + " = " + c3);
    }
}
