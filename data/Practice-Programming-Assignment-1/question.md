# Practice Programming Assignment 1

## Problem Statement
Write a program to clone an object e1 of class Employee by implementing the interface Cloneable. After cloning, update the department and the address of e1. Complete the program as detailed below to achieve this functionality.
Define classes Address and Department that implement the interface Cloneable, and have the following members:
In both classes, add an instance variable of String type (to store the address and the department respectively)
Implement the required constructor(s) and accessors.
Override the method clone.
Define a class Person that implements the interface Cloneable, and has the following members:
Instance variables name of type String and addr of type Address
Implement the required constructor(s) and accessors
Override the method clone.
Define a class Employee that implements the interface Cloneable, extends the class Person, and has the following members:
Instance variable dept of type Department
Implement the required constructor(s) and accessors.
Override the method clone.
Define a method updateEmp to update the dept and addr of an Employee object

## Test Cases
| # | Input | Expected Output |
|---|-------|-----------------|
| 1 | Vinay Kota HR<br>Mumbai Finance | Vinay : Mumbai : Finance, Vinay : Kota : HR |
| 2 | Brinda Chennai Finance<br>Kolkata IT | Brinda : Kolkata : IT, Brinda : Chennai : Finance |

## Stub Code
```java
import java.util.*;
//define class Address

//define class Department

//define class Person

//define class Employee

public class FClass{
    public static void main(String[] args){
        Scanner sc = new Scanner(System.in);
        String n = sc.next(); //read name
        String a1 = sc.next(); //read address
        String d1 = sc.next(); //read department
        String a2 = sc.next(); //read new address
        String d2 = sc.next(); //read new department
        try {
            Employee e1 = new Employee(n, new Address(a1), new Department(d1));
            Employee e2 = e1.clone();
            e1.updateEmp(a2, d2);
            System.out.println(e1 + ", " + e2);
        }
        catch(CloneNotSupportedException e) {
            System.out.println("clone() not supported");
        }
    }
}
```