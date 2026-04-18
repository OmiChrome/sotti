import java.util.*;

/**
 * QUESTION: Dynamic Dispatch - Airplane Models (July 2025 OPPE1, Question 1)
 * ============================================================================
 * Problem Statement:
 * Complete the Java code that uses the concept of inheritance to demonstrate
 * dynamic method dispatching.
 *
 * Class AirPlane has:
 *   - Private instance variable: model
 *   - Constructor to initialize model
 *   - Accessor method for model (getModel())
 *   - Method display to print: "Inside an anonymous airplane"
 *
 * Classes Boeing and AirBus should be defined so any object of Boeing or AirBus
 * can be assigned to a reference variable of type AirPlane.
 *   - Boeing.display()  prints: "Inside Boeing <model>"
 *   - AirBus.display()  prints: "Inside AirBus <model>"
 *
 * Class DispatchPlaneEx main():
 *   - Creates AirPlane[] aPlanes of size 3
 *   - aPlanes[0] = generic AirPlane("")
 *   - aPlanes[1] = Boeing(input1)
 *   - aPlanes[2] = AirBus(input2)
 *   - Calls display() on each
 *
 * What you have to do:
 *   - Define an accessor method for model inside class AirPlane
 *   - Define method display inside class AirPlane
 *   - Define classes Boeing and AirBus
 *
 * Test Cases:
 *   Input: 777X \n A350
 *   Output: Inside an anonymous airplane
 *           Inside Boeing 777X
 *           Inside AirBus A350
 *
 *   Input: 737 MAX \n A220
 *   Output: Inside an anonymous airplane
 *           Inside Boeing 737 MAX
 *           Inside AirBus A220
 */

class AirPlane {
    private String model;
    public AirPlane(String n) {
        model = n;
    }
    // Write your solution here (accessor + display)
}

// Define class Boeing here
// Define class AirBus here

public class Q12_DispatchPlaneEx {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        AirPlane[] aPlanes = new AirPlane[3];
        aPlanes[0] = new AirPlane("");
        aPlanes[1] = new Boeing(sc.nextLine());
        aPlanes[2] = new AirBus(sc.nextLine());
        aPlanes[0].display();
        aPlanes[1].display();
        aPlanes[2].display();
        sc.close();
    }
}
