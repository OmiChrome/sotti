import java.util.Scanner;

/**
 * QUESTION: Dynamic Dispatch - Vehicle (Sep 2023 OPPE1)
 * ============================================================================
 * Problem Statement:
 * Complete the Java code that uses the concept of inheritance to demonstrate
 * dynamic method dispatching.
 *
 * Create a class Vehicle with:
 *   - Private instance variable name
 *   - Constructor to initialize name
 *   - Accessor method for name
 *   - Method display to print: "This is a generic vehicle."
 *
 * Classes Car and Bicycle should be defined so that any object of Car or Bicycle
 * can be assigned to a reference variable of type Vehicle.
 *   - For Car:     display prints "This is a car named <name>."
 *   - For Bicycle: display prints "This is a bicycle named <name>."
 *
 * In DispatchExample.main(), create an array of Vehicle objects (size 3):
 *   - vehicles[0] = generic Vehicle (empty string name)
 *   - vehicles[1] = Car with name from input
 *   - vehicles[2] = Bicycle with name from input
 * Iterate the array and call display() for each.
 *
 * What you have to do: Define accessor, display in Vehicle; define Car and Bicycle.
 *
 * Test Cases:
 *   Input: BMW \n Giant
 *   Output: This is a generic vehicle.
 *           This is a car named BMW.
 *           This is a bicycle named Giant.
 */

class Vehicle {
    private String name;
    public Vehicle(String n) {
        name = n;
    }
    // Define method display
    // Define an accessor method
}

// Define class Car
// Define class Bicycle

public class Q3_DispatchExample {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        Vehicle[] vehicles = new Vehicle[3];
        vehicles[0] = new Vehicle("");
        vehicles[1] = new Car(sc.nextLine());
        vehicles[2] = new Bicycle(sc.nextLine());
        for (Vehicle v : vehicles) {
            v.display();
        }
        sc.close();
    }
}
