import java.util.*;

/**
 * QUESTION: Generics with Wildcards - Rectangle Area (Sep 2024 OPPE1, Session 1 Type 2)
 * ============================================================================
 * Problem Statement:
 * You are given two integers as input to form an object r1 of type Rectangle,
 * and two double values to form an object r2 of type Rectangle. Complete the
 * Java code to print the LARGER area among the areas of r1 and r2.
 *
 * Define a generic class Rectangle<T extends Number> with:
 *   - Instance variables: length and breadth (of type T)
 *   - Constructor to initialize the instance variables
 *   - Method area(): returns the area as double (length * breadth)
 *   - Method compareArea(Rectangle<?> rec): returns the larger area (double)
 *     between this rectangle and rec
 *
 * Class Test main():
 *   - Reads two ints → Rectangle<Integer> r1
 *   - Reads two doubles → Rectangle<Double> r2
 *   - Calls r1.compareArea(r2) and prints the result
 *
 * What you have to do: Define methods area() and compareArea() in Rectangle
 *
 * Test Cases:
 *   Input: 10 11 / 12 13    →  Output: 156.0
 *   Input: 56 78 / 34 89    →  Output: 4368.0
 *   Input: 11 11 / 11 11    →  Output: 121.0
 *   Input: 12 13 / 14.1 15.2 → Output: 214.32
 */

class Rectangle<T extends Number> {
    private T length;
    private T breadth;
    public Rectangle(T len, T bre) {
        length = len;
        breadth = bre;
    }
    // Define method: public double area() here
    // Define method: compareArea() here
}

public class Q9_Test {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        Rectangle<Integer> r1 = new Rectangle<>(sc.nextInt(), sc.nextInt());
        Rectangle<Double>  r2 = new Rectangle<>(sc.nextDouble(), sc.nextDouble());
        double large_area = r1.compareArea(r2);
        System.out.println(large_area);
    }
}
